import logging
import time
from typing import Any

from app.config import settings
from app.models import (
    AgenticMode,
    IntentProfile,
    RecommendRequest,
    RecommendResponse,
    RefineRequest,
    TrackCandidate,
)
from app.services.agent_loop import AgenticOrchestrator
from app.services.cache import TTLCache
from app.services.genius_client import GeniusClient
from app.services.openrouter_client import OpenRouterClient
from app.services.presenter import PresenterAgent
from app.services.profiler import ProfilerAgent
from app.services.ranker import RankerAgent
from app.services.spotify_client import SpotifyClient


logger = logging.getLogger(__name__)


class RecommendationPipeline:
    def __init__(
        self,
        *,
        llm: OpenRouterClient | None = None,
        spotify: SpotifyClient | None = None,
        genius: GeniusClient | None = None,
    ) -> None:
        self.llm = llm or OpenRouterClient()
        self.profiler = ProfilerAgent(self.llm)
        self.spotify = spotify or SpotifyClient()
        self.genius = genius or GeniusClient()
        self.ranker = RankerAgent(self.llm)
        self.presenter = PresenterAgent(self.llm)
        self.orchestrator = AgenticOrchestrator(self.llm, self.spotify, self.genius)
        self._profile_cache: TTLCache[IntentProfile] = TTLCache(max_size=256, ttl_seconds=600.0)
        self._search_cache: TTLCache[tuple[list[TrackCandidate], dict[str, Any]]] = TTLCache(
            max_size=128, ttl_seconds=300.0
        )

    @staticmethod
    def _profile_signature(profile: IntentProfile) -> tuple:
        return (
            profile.mood,
            profile.activity,
            tuple(profile.genre),
            profile.energy,
            profile.language,
            profile.locale,
            profile.strict_locale,
            tuple(sorted((profile.target_audio or {}).items())),
            tuple(profile.seed_genres),
        )

    async def _get_profile(self, text: str) -> tuple[IntentProfile, bool]:
        key = text.strip().lower()
        cached = self._profile_cache.get(key)
        if cached is not None:
            self.profiler.last_used_llm = False
            return cached, True
        profile = await self.profiler.profile(text)
        self._profile_cache.set(key, profile)
        return profile, False

    async def _get_candidates(
        self, profile: IntentProfile, top_k: int
    ) -> tuple[list[TrackCandidate], dict[str, Any], bool]:
        key = (self._profile_signature(profile), top_k)
        cached = self._search_cache.get(key)
        if cached is not None:
            return cached[0], cached[1], True
        result = await self.spotify.gather_candidates(profile, top_k)
        self._search_cache.set(key, result)
        return result[0], result[1], False

    async def run(self, payload: RecommendRequest) -> RecommendResponse:
        return await self._run_for_profile(
            text=payload.text,
            target_count=payload.target_count,
            agentic_mode=payload.agentic_mode,
        )

    async def run_refine(self, payload: RefineRequest) -> RecommendResponse:
        merged_text = (
            f"{payload.previous_profile.mood} {payload.previous_profile.activity} "
            f"{' '.join(payload.previous_profile.genre)} | {payload.refinement_text}"
        ).strip()
        previous_ids = set(payload.previous_track_ids or [])
        return await self._run_for_profile(
            text=merged_text,
            target_count=payload.target_count,
            previous_track_ids=previous_ids,
            refined_from=self._signature_short(payload.previous_profile),
            agentic_mode=payload.agentic_mode,
        )

    @staticmethod
    def _signature_short(profile: IntentProfile) -> str:
        return f"{profile.mood}/{profile.activity}/{'+'.join(profile.genre[:2])}/{profile.energy}"

    async def _run_for_profile(
        self,
        *,
        text: str,
        target_count: int | None,
        agentic_mode: AgenticMode = "auto",
        previous_track_ids: set[str] | None = None,
        refined_from: str | None = None,
    ) -> RecommendResponse:
        started_at = time.perf_counter()
        top_k = target_count or settings.top_k_default

        t0 = time.perf_counter()
        profile, profile_cache_hit = await self._get_profile(text)
        t1 = time.perf_counter()

        candidates, query_strategy, search_cache_hit = await self._get_candidates(profile, top_k)
        t2 = time.perf_counter()

        # Quality gate: if profile confidence is dangerously low, log a warning.
        quality_warnings: list[str] = []
        if profile.confidence < 0.3:
            quality_warnings.append(f"low_profile_confidence ({profile.confidence:.2f})")
            logger.warning("Low profile confidence: %.2f for text: %s", profile.confidence, text[:80])

        if previous_track_ids:
            original_count = len(candidates)
            candidates = [c for c in candidates if c.track_id not in previous_track_ids]
            excluded_count = original_count - len(candidates)
            if excluded_count:
                quality_warnings.append(f"refine_previous_tracks_excluded ({excluded_count})")
            if len(candidates) < top_k:
                quality_warnings.append(f"refine_candidate_pool_short ({len(candidates)} < {top_k})")

        lyric_candidates = self.ranker.preselect_for_lyrics(
            profile,
            candidates,
            settings.genius_lyrics_top_n,
        )
        lyric_info = await self.genius.enrich_candidates(
            profile,
            lyric_candidates,
            limit=len(lyric_candidates),
        )

        # Optional agentic loop (opt-in).
        agentic_notes = self._initial_agentic_notes(agentic_mode)
        should_run_agentic = self._should_run_agentic(agentic_mode, agentic_notes)
        if should_run_agentic:
            try:
                result = await self.orchestrator.run(
                    profile,
                    candidates,
                    top_k,
                    force=(agentic_mode == "agentic"),
                )
                if result is not None:
                    candidates, agent_info = result
                    self._merge_agentic_info(agentic_notes, agent_info)
                else:
                    agentic_notes["mode_effective"] = "linear"
                    agentic_notes["status"] = "fallback"
                    agentic_notes["fallback_reason"] = "Agent loop returned no result."
            except Exception as exc:
                logger.warning("Agent loop failed, falling back to linear: %s", exc)
                agentic_notes["mode_effective"] = "linear"
                agentic_notes["status"] = "failed"
                agentic_notes["fallback_reason"] = "Agent loop failed; used linear pipeline."

        if len(candidates) < max(int(top_k * 0.6), 5):
            quality_warnings.append(f"candidate_pool_small ({len(candidates)} < {int(top_k * 0.6)})")

        ranked = await self.ranker.rank(profile, candidates, top_k=top_k)
        t3 = time.perf_counter()

        if ranked:
            avg_score = sum(c.score for c in ranked) / len(ranked)
            if avg_score < 0.35:
                quality_warnings.append(f"low_average_score ({avg_score:.2f})")

        presented = await self.presenter.present(profile, ranked)
        t4 = time.perf_counter()

        fallback_used = len(ranked) < top_k
        fallback_reason = "" if not fallback_used else "Candidates kurang dari target_count setelah ranking."

        notes: dict[str, Any] = {
            "deduplicated": True,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "llm_profiler_used": self.profiler.last_used_llm,
            "llm_ranker_used": self.ranker.last_used_llm,
            "llm_presenter_used": self.presenter.last_used_llm,
            "llm_enabled": self.llm.enabled,
            "agent_loop_enabled": settings.agent_loop_enabled,
            "agent_iterations": agentic_notes["iterations"],
            "tools_called": agentic_notes["tools_called"],
            "agentic": agentic_notes,
            "lyrics": lyric_info,
            "cache_hits": {"profile": profile_cache_hit, "search": search_cache_hit},
            "quality_warnings": quality_warnings,
            "stage_ms": {
                "profiler": int((t1 - t0) * 1000),
                "search": int((t2 - t1) * 1000),
                "ranker": int((t3 - t2) * 1000),
                "presenter": int((t4 - t3) * 1000),
                "total": int((t4 - started_at) * 1000),
            },
        }
        if refined_from:
            notes["refined_from"] = refined_from

        return RecommendResponse(
            summary={
                "input_language": profile.language,
                "intent_text": text,
                "target_count": top_k,
                "returned_count": len(presented),
            },
            intent_profile=profile,
            query_strategy=query_strategy,
            recommendations=presented,
            quality_notes=notes,
        )

    def _initial_agentic_notes(self, requested: AgenticMode) -> dict[str, Any]:
        status = "disabled"
        fallback_reason = ""
        if requested == "linear":
            status = "bypassed"
        elif requested == "agentic" and not self.llm.enabled:
            status = "unavailable_llm"
            fallback_reason = "LLM is disabled."
        elif requested == "auto" and not settings.agent_loop_enabled:
            status = "disabled"
            fallback_reason = "AGENT_LOOP_ENABLED is false."
        elif requested == "auto" and not self.llm.enabled:
            status = "unavailable_llm"
            fallback_reason = "LLM is disabled."
        elif requested in {"auto", "agentic"}:
            status = "pending"

        return {
            "mode_requested": requested,
            "mode_effective": "linear",
            "status": status,
            "iterations": 0,
            "tools_called": [],
            "trace": [],
            "finalized": False,
            "fallback_reason": fallback_reason,
        }

    def _should_run_agentic(self, requested: AgenticMode, notes: dict[str, Any]) -> bool:
        if requested == "linear" or not self.llm.enabled:
            return False
        if requested == "agentic":
            notes["mode_effective"] = "agentic"
            return True
        if settings.agent_loop_enabled:
            notes["mode_effective"] = "agentic"
            return True
        return False

    @staticmethod
    def _merge_agentic_info(notes: dict[str, Any], info: dict[str, Any]) -> None:
        notes["mode_effective"] = "agentic"
        notes["status"] = info.get("status") or "completed"
        notes["iterations"] = int(info.get("iterations", 0) or 0)
        notes["tools_called"] = list(info.get("tools_called", []) or [])
        notes["trace"] = list(info.get("trace", []) or [])
        notes["finalized"] = bool(info.get("finalized", False))
        notes["fallback_reason"] = str(info.get("fallback_reason", "") or "")
