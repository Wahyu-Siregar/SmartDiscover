"""Agentic orchestrator with tool-use loop.

The orchestrator gives the LLM a small toolbox to iteratively shape the
candidate list before final ranking. It is OPT-IN via AGENT_LOOP_ENABLED
to keep latency and cost bounded for the default flow.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from app.config import settings
from app.models import IntentProfile, TrackCandidate
from app.services.genius_client import GeniusClient
from app.services.openrouter_client import OpenRouterClient
from app.services.spotify_client import SpotifyClient


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "request_more_candidates",
            "description": "Search Spotify with an additional natural-language query and append more tracks to the candidate pool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Free-text search query, e.g. 'lo-fi study indonesia'"},
                    "count": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_lyric_signals",
            "description": "Fetch bounded Genius lyric metadata/signals for selected tracks only. Use when lyrics/themes are important to the intent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["track_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_by_audio",
            "description": "Filter the current candidate pool by audio feature ranges. Use this to demote or drop tracks whose features mismatch the intent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_energy": {"type": "number"},
                    "max_energy": {"type": "number"},
                    "min_valence": {"type": "number"},
                    "max_valence": {"type": "number"},
                    "min_tempo": {"type": "number"},
                    "max_tempo": {"type": "number"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_audio_features",
            "description": "Force re-fetch audio features for tracks that are missing them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["track_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalize",
            "description": "Stop iterating and finalize the candidate pool. Provide the chosen track_ids in preferred order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track_ids": {"type": "array", "items": {"type": "string"}},
                    "reasoning": {"type": "string"},
                },
                "required": ["track_ids"],
            },
        },
    },
]


SYSTEM_PROMPT = (
    "You are SmartDiscover Orchestrator. You have a candidate pool of music tracks and an intent profile. "
    "Your job is to refine the pool to the best top_k tracks for the user. "
    "Use tools when the pool is too small, too homogeneous, or audio features mismatch the intent. "
    "Use lyric signals for lyric/theme-sensitive prompts, but only for a small selected subset. "
    "Call `finalize` as soon as you are satisfied (max 3 iterations). "
    "Avoid more than 2 tracks from the same artist. Prefer tracks with audio features and lyric signals matching the intent."
)


class AgenticOrchestrator:
    def __init__(self, llm: OpenRouterClient, spotify: SpotifyClient, genius: GeniusClient | None = None) -> None:
        self.llm = llm
        self.spotify = spotify
        self.genius = genius or GeniusClient()

    async def run(
        self,
        profile: IntentProfile,
        candidates: list[TrackCandidate],
        target_count: int,
    ) -> tuple[list[TrackCandidate], dict[str, Any]] | None:
        """Run the agentic loop. Returns (refined_candidates, info) or None on disabled/failure."""
        if not settings.agent_loop_enabled or not self.llm.enabled or not candidates:
            return None

        pool: dict[str, TrackCandidate] = {
            (c.track_id or f"local_{i}"): c for i, c in enumerate(candidates)
        }
        finalized_order: list[str] = []
        deadline = time.monotonic() + settings.agent_loop_timeout_s
        info: dict[str, Any] = {"tools_called": [], "iterations": 0}

        async def tool_executor(name: str, args: dict[str, Any]) -> Any:
            if time.monotonic() > deadline:
                return {"error": "timeout"}

            info["tools_called"].append(name)

            if name == "request_more_candidates":
                query = str(args.get("query", "")).strip()
                count = int(args.get("count", 10))
                if not query:
                    return {"added": 0}
                added = await self._search_more(query, profile, count)
                new_count = 0
                for c in added:
                    key = c.track_id or f"local_{len(pool)}"
                    if key not in pool:
                        pool[key] = c
                        new_count += 1
                return {
                    "added": new_count,
                    "pool_size": len(pool),
                    "preview": [
                        {"track_id": c.track_id, "title": c.title, "artist": c.artist}
                        for c in added[:5]
                    ],
                }

            if name == "filter_by_audio":
                kept = self._filter_by_audio(list(pool.values()), args)
                kept_ids = {c.track_id or "" for c in kept}
                removed = 0
                for key in list(pool.keys()):
                    if (pool[key].track_id or "") not in kept_ids:
                        pool.pop(key, None)
                        removed += 1
                return {"removed": removed, "pool_size": len(pool)}

            if name == "request_audio_features":
                ids = [str(t) for t in args.get("track_ids", []) if t]
                if not ids:
                    return {"updated": 0}
                features = await self.spotify.get_audio_features(ids)
                updated = 0
                for c in pool.values():
                    if c.track_id in features and not c.audio_features:
                        c.audio_features = features[c.track_id]
                        updated += 1
                return {"updated": updated}

            if name == "request_lyric_signals":
                ids = [str(t) for t in args.get("track_ids", []) if t]
                if not ids:
                    return {"updated": 0}
                selected = [c for c in pool.values() if c.track_id in ids]
                lyric_info = await self.genius.enrich_candidates(profile, selected, limit=min(len(selected), 10))
                return {"updated": lyric_info.get("filled", 0), "lookups": lyric_info.get("lookups", 0)}

            if name == "finalize":
                ids = [str(t) for t in args.get("track_ids", []) if t]
                finalized_order.extend(ids)
                return {"accepted": len(ids), "reasoning_recorded": bool(args.get("reasoning"))}

            return {"error": f"unknown tool: {name}"}

        # Build initial user prompt with compact pool view.
        pool_view = [
            {
                "track_id": c.track_id,
                "title": c.title,
                "artist": c.artist,
                "audio": (
                    {k: round(v, 3) for k, v in c.audio_features.items() if k in {"energy", "valence", "tempo"}}
                    if c.audio_features
                    else None
                ),
                "lyrics": (
                    {
                        "themes": c.lyric_signals.get("themes", [])[:4],
                        "sentiment": c.lyric_signals.get("sentiment", ""),
                        "match_score": c.lyric_signals.get("match_score", 0),
                    }
                    if c.lyric_signals
                    else None
                ),
            }
            for c in list(pool.values())[:60]
        ]
        user_prompt = (
            f"intent_profile={profile.model_dump()}\n"
            f"target_count={target_count}\n"
            f"pool_size={len(pool)}\n"
            f"sample={pool_view}\n"
            "Refine the pool then call `finalize`."
        )

        try:
            result = await asyncio.wait_for(
                self.llm.chat_with_tools(
                    SYSTEM_PROMPT,
                    user_prompt,
                    tools=TOOL_DEFINITIONS,
                    tool_executor=tool_executor,
                    max_iterations=settings.agent_loop_max_iterations,
                    max_tokens=1200,
                    temperature=0.2,
                ),
                timeout=settings.agent_loop_timeout_s,
            )
        except asyncio.TimeoutError:
            info["timeout"] = True
            result = None

        if not result:
            return None

        info["iterations"] = result.get("iterations", 0)
        info["trace"] = result.get("trace", [])

        # Apply finalize order if any; otherwise use current pool order.
        if finalized_order:
            ordered: list[TrackCandidate] = []
            seen: set[str] = set()
            for tid in finalized_order:
                c = pool.get(tid)
                if c is None:
                    # Try matching by track_id field.
                    for v in pool.values():
                        if v.track_id == tid:
                            c = v
                            break
                if c and c.track_id not in seen:
                    ordered.append(c)
                    if c.track_id:
                        seen.add(c.track_id)
            # Append remaining pool items (in case finalize was incomplete).
            for c in pool.values():
                key = c.track_id or ""
                if key not in seen:
                    ordered.append(c)
                    seen.add(key)
            return ordered, info

        return list(pool.values()), info

    async def _search_more(
        self, query: str, profile: IntentProfile, count: int
    ) -> list[TrackCandidate]:
        token = await self.spotify._get_access_token()  # pragma: no cover - thin wrapper
        market = self.spotify.resolve_market(profile)
        headers = {"Authorization": f"Bearer {token}"}
        resp = await self.spotify._request_with_retry(
            "GET",
            self.spotify.SEARCH_URL,
            params={"q": query, "type": "track", "limit": min(20, max(1, count)), "market": market},
            headers=headers,
        )
        if resp is None or resp.status_code != 200:
            return []

        items = resp.json().get("tracks", {}).get("items", [])
        out: list[TrackCandidate] = []
        for item in items:
            if not item or not item.get("id"):
                continue
            out.append(
                TrackCandidate(
                    title=item.get("name", ""),
                    artist=", ".join(a.get("name", "") for a in item.get("artists", [])),
                    track_id=item["id"],
                    spotify_url=item.get("external_urls", {}).get("spotify", ""),
                    preview_url=item.get("preview_url") or "",
                    popularity=item.get("popularity", 0),
                    artist_ids=[a.get("id", "") for a in item.get("artists", []) if a.get("id")],
                )
            )

        # Best-effort enrich.
        if out:
            track_ids = [c.track_id for c in out if c.track_id]
            try:
                features = await self.spotify.get_audio_features(track_ids)
            except Exception:
                features = {}
            for c in out:
                if c.track_id in features:
                    c.audio_features = features[c.track_id]
        return out

    @staticmethod
    def _filter_by_audio(
        candidates: list[TrackCandidate], constraints: dict[str, Any]
    ) -> list[TrackCandidate]:
        def keep(c: TrackCandidate) -> bool:
            if not c.audio_features:
                # No data → keep (don't penalize unknowns aggressively).
                return True
            af = c.audio_features
            checks: list[bool] = []
            for key, op_min, op_max in (
                ("energy", "min_energy", "max_energy"),
                ("valence", "min_valence", "max_valence"),
                ("tempo", "min_tempo", "max_tempo"),
            ):
                if key not in af:
                    continue
                if op_min in constraints:
                    try:
                        checks.append(af[key] >= float(constraints[op_min]))
                    except Exception:
                        pass
                if op_max in constraints:
                    try:
                        checks.append(af[key] <= float(constraints[op_max]))
                    except Exception:
                        pass
            return all(checks) if checks else True

        return [c for c in candidates if keep(c)]
