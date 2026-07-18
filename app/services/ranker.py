import math
from typing import Any

from app.models import IntentProfile, TrackCandidate
from app.services.openrouter_client import OpenRouterClient


GENRE_HINTS = {
    "batak": ["batak", "toba", "mandailing", "karo", "simalungun", "pakpak"],
    "jawa": ["jawa", "javanese", "campursari", "keroncong", "koplo"],
    "minang": ["minang", "minangkabau", "padang"],
}

DEFAULT_MAX_PER_ARTIST = 2

# Audio feature comparison weights for euclidean distance (only normalized 0..1 keys).
_AUDIO_DISTANCE_KEYS = ("energy", "valence", "danceability", "acousticness", "instrumentalness")


class RankerAgent:
    def __init__(self, llm: OpenRouterClient, *, max_per_artist: int = DEFAULT_MAX_PER_ARTIST) -> None:
        self.llm = llm
        self.last_used_llm = False
        self.max_per_artist = max_per_artist

    async def rank(
        self, profile: IntentProfile, candidates: list[TrackCandidate], top_k: int
    ) -> list[TrackCandidate]:
        deduped = self._dedupe(candidates)

        # Always score with heuristic first; used as fallback fill and as scores
        # for tracks the LLM might omit.
        heuristic_scored = sorted(
            (self._score(profile, c) for c in deduped),
            key=lambda x: x.score,
            reverse=True,
        )

        llm_ranked = await self._rank_with_llm(profile, deduped, top_k)
        if llm_ranked is not None:
            self.last_used_llm = True
            # Pass a generously sized pool so diversity has overflow to redistribute.
            merged = self._fill_min_output(llm_ranked, heuristic_scored, max(top_k * 3, top_k + 5))
        else:
            self.last_used_llm = False
            merged = heuristic_scored

        return self._enforce_artist_diversity(merged, top_k)

    def preselect_for_lyrics(
        self,
        profile: IntentProfile,
        candidates: list[TrackCandidate],
        limit: int,
    ) -> list[TrackCandidate]:
        if limit <= 0:
            return []
        return sorted(
            (self._score(profile, candidate) for candidate in self._dedupe(candidates)),
            key=lambda candidate: candidate.score,
            reverse=True,
        )[:limit]

    # ---- LLM ranker --------------------------------------------------

    async def _rank_with_llm(
        self,
        profile: IntentProfile,
        candidates: list[TrackCandidate],
        top_k: int,
    ) -> list[TrackCandidate] | None:
        if not self.llm.enabled or not candidates:
            return None

        rows: list[dict[str, Any]] = []
        for idx, c in enumerate(candidates, start=1):
            row: dict[str, Any] = {
                "idx": idx,
                "title": c.title,
                "artist": c.artist,
                "popularity": c.popularity,
            }
            if c.audio_features:
                row["audio"] = {
                    k: round(v, 3)
                    for k, v in c.audio_features.items()
                    if k in {"energy", "valence", "danceability", "tempo", "acousticness", "instrumentalness"}
                }
            if c.genres:
                row["genres"] = c.genres[:5]
            if c.lyric_signals:
                row["lyrics"] = {
                    "themes": c.lyric_signals.get("themes", [])[:4],
                    "sentiment": c.lyric_signals.get("sentiment", ""),
                    "summary": c.lyric_signals.get("summary", ""),
                    "match_score": c.lyric_signals.get("match_score", 0),
                    "confidence": c.lyric_signals.get("confidence", 0),
                    "source_kind": c.lyric_signals.get("source_kind", ""),
                }
            rows.append(row)

        system_prompt = (
            "You are Filter and Ranker Agent for music recommendations. "
            "Rank candidates by fit to intent_profile. Use provided audio features and genres "
            "and lyric signals to make objective decisions; do not rely solely on title or artist name. "
            "Lyric evidence is metadata-only unless source_kind explicitly says otherwise; "
            "do not claim to know the full lyric meaning and weigh low-confidence evidence lightly. "
            "Return JSON only with key 'ranked'. Each item must include idx, score (0..1), why (short, 1 sentence). "
            "Diversity rule: avoid more than 2 tracks from the same artist; prefer variety. "
            "If audio features deviate strongly from intent_profile.target_audio (e.g. energy mismatch >0.3), demote. "
            "If intent_profile has locale and strict_locale=true, strongly prioritize tracks matching that locale. "
            "Always return at least min(top_k, len(candidates)) items, sorted best-first. "
            "Optionally include key 'excluded' as list of {idx, reason} for transparency."
        )
        user_prompt = (
            f"intent_profile={profile.model_dump()}\n"
            f"top_k={top_k}\n"
            f"candidates={rows}"
        )
        data = await self.llm.chat_json(system_prompt, user_prompt, max_tokens=1600, json_mode=True)
        if not data or not isinstance(data.get("ranked"), list):
            return None

        idx_map = {i + 1: c for i, c in enumerate(candidates)}
        output: list[TrackCandidate] = []
        used: set[int] = set()
        for item in data["ranked"]:
            try:
                idx = int(item.get("idx"))
                if idx in used or idx not in idx_map:
                    continue
                used.add(idx)
                base = idx_map[idx]
                score = float(item.get("score", 0.0))
                base.score = round(max(0.0, min(1.0, score)), 4)
                why = str(item.get("why", "")).strip()
                if why:
                    base.why = why
                output.append(base)
            except Exception:
                continue

        return output if output else None

    # ---- Min-output guard --------------------------------------------

    def _fill_min_output(
        self,
        llm_ranked: list[TrackCandidate],
        heuristic_sorted: list[TrackCandidate],
        top_k: int,
    ) -> list[TrackCandidate]:
        if len(llm_ranked) >= top_k:
            return llm_ranked[:top_k]

        seen_ids = {self._dedupe_key(c) for c in llm_ranked}
        filler: list[TrackCandidate] = []
        for c in heuristic_sorted:
            if self._dedupe_key(c) in seen_ids:
                continue
            filler.append(c)
            seen_ids.add(self._dedupe_key(c))
            if len(llm_ranked) + len(filler) >= top_k:
                break

        return (llm_ranked + filler)[:top_k]

    # ---- Artist diversity ---------------------------------------------

    def _enforce_artist_diversity(
        self, ranked: list[TrackCandidate], top_k: int
    ) -> list[TrackCandidate]:
        if not ranked or self.max_per_artist <= 0:
            return ranked[:top_k]

        primary: list[TrackCandidate] = []
        overflow: list[TrackCandidate] = []
        per_artist: dict[str, int] = {}
        for c in ranked:
            key = self._artist_key(c)
            count = per_artist.get(key, 0)
            if count < self.max_per_artist:
                primary.append(c)
                per_artist[key] = count + 1
            else:
                overflow.append(c)
            if len(primary) >= top_k:
                break

        if len(primary) >= top_k:
            return primary[:top_k]

        return (primary + overflow)[:top_k]

    @staticmethod
    def _artist_key(candidate: TrackCandidate) -> str:
        if candidate.artist_ids:
            return f"id::{candidate.artist_ids[0]}"
        return f"name::{candidate.artist.lower().split(',')[0].strip()}"

    # ---- Dedupe -------------------------------------------------------

    def _dedupe(self, candidates: list[TrackCandidate]) -> list[TrackCandidate]:
        seen: set[str] = set()
        output: list[TrackCandidate] = []
        for c in candidates:
            key = self._dedupe_key(c)
            if key in seen:
                continue
            seen.add(key)
            output.append(c)
        return output

    @staticmethod
    def _dedupe_key(c: TrackCandidate) -> str:
        if c.track_id:
            return f"id::{c.track_id}"
        return f"name::{c.title.lower()}::{c.artist.lower()}"

    # ---- Heuristic scoring -------------------------------------------

    def _score(self, profile: IntentProfile, candidate: TrackCandidate) -> TrackCandidate:
        text = f"{candidate.title} {candidate.artist}".lower()

        relevance = 0.25
        if profile.mood in text:
            relevance += 0.25
        if profile.activity in text:
            relevance += 0.20

        # Genre boost via title/artist text (legacy) and via Spotify-provided artist genres.
        genre_text_match = False
        for genre in profile.genre:
            genre_lower = genre.lower()
            hints = GENRE_HINTS.get(genre_lower, [genre_lower])
            if any(h in text for h in hints):
                genre_text_match = True
                relevance += 0.30
            elif candidate.genres:
                if any(genre_lower in g.lower() for g in candidate.genres):
                    relevance += 0.25
                    genre_text_match = True
        if profile.genre and not genre_text_match and len(profile.genre) == 1:
            relevance -= 0.06

        mood_energy_fit = 0.10
        if profile.energy == "low" and any(k in text for k in ["quiet", "soft", "calm", "slow"]):
            mood_energy_fit += 0.30
        if profile.energy == "high" and any(k in text for k in ["run", "fast", "boost", "pulse"]):
            mood_energy_fit += 0.30

        # Audio-feature aware bonus: similarity to target_audio.
        audio_bonus = 0.0
        if candidate.audio_features and profile.target_audio:
            audio_bonus = self._audio_similarity_bonus(candidate.audio_features, profile.target_audio)

        lyric_bonus = 0.0
        if candidate.lyric_signals:
            lyric_bonus = self._lyric_signal_bonus(profile, candidate.lyric_signals)

        popularity = candidate.popularity / 100

        diversity_bonus = min(1.0, len(set(candidate.title.lower().split())) / 5)

        locale_bonus = 0.0
        if profile.locale == "indonesia":
            locale_terms = ["indonesia", "indonesian", "nusantara", "tanah air", "merah putih", "garuda"]
            locale_match = any(term in text for term in locale_terms)
            if locale_match:
                locale_bonus = 0.20 if profile.strict_locale else 0.10
            elif profile.strict_locale:
                locale_bonus = -0.20

        score = (
            (relevance * 0.40)
            + (mood_energy_fit * 0.15)
            + (audio_bonus * 0.25)
            + (lyric_bonus * 0.12)
            + (popularity * 0.08)
            + (diversity_bonus * 0.10)
            + locale_bonus
        )
        candidate.score = round(max(0.0, min(1.0, score)), 4)
        return candidate

    @staticmethod
    def _audio_similarity_bonus(features: dict[str, float], target: dict[str, float]) -> float:
        # Euclidean distance over normalized [0..1] keys present in both.
        diffs: list[float] = []
        for key in _AUDIO_DISTANCE_KEYS:
            if key in features and key in target:
                diffs.append(features[key] - target[key])

        if "tempo" in features and "tempo" in target:
            tempo_diff = (features["tempo"] - target["tempo"]) / 60.0
            diffs.append(tempo_diff)

        if not diffs:
            return 0.0

        distance = math.sqrt(sum(d * d for d in diffs)) / math.sqrt(len(diffs))
        # Map distance 0 -> 1.0, distance >=0.7 -> 0.0
        return max(0.0, min(1.0, 1.0 - (distance / 0.7)))

    @staticmethod
    def _lyric_signal_bonus(profile: IntentProfile, signals: dict[str, Any]) -> float:
        score = float(signals.get("match_score") or 0.0)
        try:
            confidence = float(signals.get("confidence", 1.0))
        except (TypeError, ValueError):
            confidence = 0.0
        themes = set(signals.get("themes") or [])
        sentiment = str(signals.get("sentiment") or "")
        if profile.mood in {"sad", "melancholy", "galau"} and sentiment == "sad":
            score = max(score, 0.75)
        if profile.energy == "high" and themes.intersection({"party", "confidence"}):
            score = max(score, 0.7)
        if profile.energy == "low" and themes.intersection({"calm", "heartbreak", "longing"}):
            score = max(score, 0.7)
        return max(0.0, min(1.0, score)) * max(0.0, min(1.0, confidence))
