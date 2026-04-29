from typing import Any

from app.models import IntentProfile, RecommendationItem, TrackCandidate
from app.services.openrouter_client import OpenRouterClient


class PresenterAgent:
    def __init__(self, llm: OpenRouterClient | None = None) -> None:
        self.llm = llm
        self.last_used_llm = False

    async def present(
        self, profile: IntentProfile, tracks: list[TrackCandidate]
    ) -> list[RecommendationItem]:
        # If any track is missing a `why`, batch-generate them via LLM (single call).
        await self._maybe_generate_reasons(profile, tracks)

        items: list[RecommendationItem] = []
        for idx, track in enumerate(tracks, start=1):
            reason = self._build_reason(profile, track)
            items.append(
                RecommendationItem(
                    rank=idx,
                    title=track.title,
                    artist=track.artist,
                    track_id=track.track_id,
                    spotify_url=track.spotify_url,
                    preview_url=track.preview_url,
                    why=reason,
                    score=track.score,
                )
            )
        return items

    async def _maybe_generate_reasons(
        self, profile: IntentProfile, tracks: list[TrackCandidate]
    ) -> None:
        self.last_used_llm = False
        if not self.llm or not self.llm.enabled:
            return

        missing = [t for t in tracks if not t.why.strip()]
        if not missing:
            return

        rows: list[dict[str, Any]] = []
        for idx, track in enumerate(missing, start=1):
            row: dict[str, Any] = {"idx": idx, "title": track.title, "artist": track.artist}
            if track.audio_features:
                row["audio"] = {
                    k: round(v, 3)
                    for k, v in track.audio_features.items()
                    if k in {"energy", "valence", "danceability", "tempo"}
                }
            if track.genres:
                row["genres"] = track.genres[:3]
            rows.append(row)

        system_prompt = (
            "You are Presenter Agent for SmartDiscover. "
            "For each candidate, write ONE concise sentence (max 18 words) explaining why it fits the user's intent. "
            "Use audio cues and genres when relevant. Match the user's language (id or en). "
            "Return strict JSON: {\"reasons\":[{\"idx\":int,\"why\":string}, ...]}"
        )
        user_prompt = (
            f"intent_profile={profile.model_dump()}\n"
            f"language={profile.language}\n"
            f"candidates={rows}"
        )
        data = await self.llm.chat_json(system_prompt, user_prompt, max_tokens=900, json_mode=True)
        if not data or not isinstance(data.get("reasons"), list):
            return

        idx_to_track = {i + 1: t for i, t in enumerate(missing)}
        applied = 0
        for entry in data["reasons"]:
            try:
                idx = int(entry.get("idx"))
                why = str(entry.get("why", "")).strip()
                target = idx_to_track.get(idx)
                if target and why and not target.why.strip():
                    target.why = why
                    applied += 1
            except Exception:
                continue
        if applied:
            self.last_used_llm = True

    # ---- Fallback template ------------------------------------------

    def _build_reason(self, profile: IntentProfile, track: TrackCandidate) -> str:
        if track.why.strip():
            return track.why
        locale_hint = ""
        if profile.locale:
            locale_hint = (
                f" dengan konteks {profile.locale}"
                if profile.language == "id"
                else f" with {profile.locale} context"
            )
        if profile.language == "id":
            return f"Cocok untuk {profile.activity} dengan nuansa {profile.mood} dan energi {profile.energy}{locale_hint}."
        return f"Good fit for {profile.activity} with a {profile.mood} mood and {profile.energy} energy{locale_hint}."
