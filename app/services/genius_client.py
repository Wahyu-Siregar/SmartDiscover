import asyncio
import re
from typing import Any

import httpx

from app.config import settings
from app.models import IntentProfile, TrackCandidate
from app.services.cache import TTLCache
from app.services.embedding_service import E5SemanticMatcher


THEME_KEYWORDS = {
    "heartbreak": ["heartbreak", "broken", "breakup", "kecewa", "patah hati", "ditinggal"],
    "longing": ["miss", "missing", "rindu", "kangen", "longing"],
    "nostalgia": ["memory", "memories", "nostalgia", "dulu", "kenangan"],
    "confidence": ["win", "champion", "power", "strong", "percaya diri", "semangat"],
    "party": ["party", "dance", "club", "pesta", "dansa"],
    "calm": ["calm", "quiet", "soft", "tenang", "sunyi"],
    "patriotic": ["indonesia", "merdeka", "garuda", "nusantara", "tanah air"],
}

NEGATIVE_WORDS = {"sad", "cry", "tears", "broken", "lonely", "sedih", "sakit", "kecewa", "hancur"}
POSITIVE_WORDS = {"happy", "love", "party", "dance", "win", "bright", "bahagia", "senang", "semangat"}
ID_WORDS = {"aku", "kamu", "rindu", "cinta", "hati", "lagu", "sedih", "bahagia", "indonesia"}


class GeniusClient:
    BASE_URL = "https://api.genius.com"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        semantic_matcher: E5SemanticMatcher | None = None,
    ) -> None:
        self._client = client
        self._semantic_matcher = semantic_matcher or E5SemanticMatcher()
        self._cache: TTLCache[dict[str, Any] | None] = TTLCache(
            max_size=512,
            ttl_seconds=float(settings.genius_lyrics_cache_ttl_s),
        )

    def attach_client(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return bool(settings.genius_lyrics_enabled and settings.genius_access_token)

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("GeniusClient.attach_client() must be called before use")
        return self._client

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.genius_access_token}"}

    async def enrich_candidates(
        self,
        profile: IntentProfile,
        candidates: list[TrackCandidate],
        *,
        limit: int | None = None,
    ) -> dict[str, Any]:
        if not self.enabled or not candidates:
            return {"enabled": self.enabled, "lookups": 0, "filled": 0, "source": "genius"}

        safe_limit = max(0, min(limit or settings.genius_lyrics_top_n, len(candidates)))
        if safe_limit <= 0:
            return {"enabled": True, "lookups": 0, "filled": 0, "source": "genius"}

        selected = candidates[:safe_limit]
        metadata_rows = await asyncio.gather(
            *[self.lookup_track(track) for track in selected],
            return_exceptions=True,
        )

        filled = 0
        semantic_rows: list[tuple[dict[str, Any], str]] = []
        for track, metadata in zip(selected, metadata_rows):
            if isinstance(metadata, Exception) or not metadata:
                continue
            result = metadata.get("result", {}) or {}
            song = metadata.get("song", {}) or {}
            signal = self._build_signal(profile, track, result, song)
            track.lyric_signals = signal
            filled += 1
            description = self._description_text(song)
            if profile.meaning_required and profile.lyrical_intent and description:
                semantic_rows.append((signal, description))

        if semantic_rows:
            passages = [description for _, description in semantic_rows]
            raw_scores = await asyncio.to_thread(
                self._semantic_matcher.score,
                profile.lyrical_intent,
                passages,
            )
            if len(raw_scores) != len(semantic_rows):
                raise RuntimeError("E5 matcher returned an unexpected score count")
            relative_scores = self._relative_scores(raw_scores)
            for (signal, _), raw_score, relative_score in zip(
                semantic_rows,
                raw_scores,
                relative_scores,
            ):
                signal["semantic_score"] = round(float(raw_score), 6)
                signal["semantic_model"] = self._semantic_matcher.MODEL_ID
                signal["match_score"] = relative_score

        return {"enabled": True, "lookups": safe_limit, "filled": filled, "source": "genius"}

    async def lookup_track(self, track: TrackCandidate) -> dict[str, Any] | None:
        key = self._cache_key(track)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        query = f"{track.title} {track.artist}".strip()
        if not query:
            return None

        client = self._require_client()
        try:
            search_resp = await client.get(
                f"{self.BASE_URL}/search",
                params={"q": query},
                headers=self._headers(),
                timeout=12.0,
            )
            if search_resp.status_code != 200:
                return None
            hit = self._best_hit(track, search_resp.json().get("response", {}).get("hits", []) or [])
            if not hit:
                return None

            result = hit.get("result", {}) or {}
            metadata = {"result": result, "song": await self._fetch_song(result.get("id"))}
            self._cache.set(key, metadata)
            return metadata
        except Exception:
            return None

    async def _fetch_song(self, song_id: Any) -> dict[str, Any]:
        if not song_id:
            return {}
        client = self._require_client()
        try:
            resp = await client.get(
                f"{self.BASE_URL}/songs/{song_id}",
                headers=self._headers(),
                timeout=12.0,
            )
            if resp.status_code != 200:
                return {}
            return resp.json().get("response", {}).get("song", {}) or {}
        except Exception:
            return {}

    def _build_signal(
        self,
        profile: IntentProfile,
        track: TrackCandidate,
        result: dict[str, Any],
        song: dict[str, Any],
    ) -> dict[str, Any]:
        description = self._normalize_text(self._description_text(song))
        source_kind = "metadata_description" if description else "metadata_title_only"
        themes = self._themes(description) if description else []
        sentiment = self._sentiment(description) if description else "unknown"
        language = (
            "id"
            if description and any(self._contains_term(description, word) for word in ID_WORDS)
            else profile.language
        )
        match_score = self._match_score(profile, description, themes, sentiment, language) if description else 0.0

        return {
            "source": "genius",
            "source_kind": source_kind,
            "source_url": result.get("url") or song.get("url") or "",
            "lyrics_state": song.get("lyrics_state") or result.get("lyrics_state") or "unknown",
            "language": language,
            "themes": themes,
            "sentiment": sentiment,
            "summary": self._summary(language, themes, sentiment, source_kind),
            "match_score": match_score,
            "confidence": 0.45 if description else 0.1,
            "note": "Metadata-only signal; the official Genius API does not return full lyrics.",
        }

    @staticmethod
    def _cache_key(track: TrackCandidate) -> str:
        if track.track_id:
            return f"spotify::{track.track_id}"
        return f"name::{track.title.lower()}::{track.artist.lower()}"

    @staticmethod
    def _description_text(song: dict[str, Any]) -> str:
        return re.sub(r"\s+", " ", str(song.get("description_preview") or "")).strip()

    @staticmethod
    def _relative_scores(scores: list[float]) -> list[float]:
        if not scores:
            return []
        low = min(scores)
        high = max(scores)
        if len(scores) == 1 or high - low <= 1e-9:
            return [0.5] * len(scores)
        return [round((score - low) / (high - low), 4) for score in scores]

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    @staticmethod
    def _best_hit(track: TrackCandidate, hits: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not hits:
            return None
        title = track.title.lower()
        artist = track.artist.lower().split(",")[0].strip()
        for hit in hits[:5]:
            result = hit.get("result", {}) or {}
            hit_title = str(result.get("title") or "").lower()
            hit_artist = str((result.get("primary_artist") or {}).get("name") or "").lower()
            if (
                title
                and hit_title
                and (title in hit_title or hit_title in title)
                and artist
                and hit_artist
                and artist in hit_artist
            ):
                return hit
        return None

    @staticmethod
    def _contains_term(text: str, term: str) -> bool:
        return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))

    @classmethod
    def _themes(cls, text: str) -> list[str]:
        themes = [theme for theme, words in THEME_KEYWORDS.items() if any(cls._contains_term(text, word) for word in words)]
        return themes[:4]

    @classmethod
    def _sentiment(cls, text: str) -> str:
        negative = sum(1 for word in NEGATIVE_WORDS if cls._contains_non_negated_term(text, word))
        positive = sum(1 for word in POSITIVE_WORDS if cls._contains_non_negated_term(text, word))
        if negative > positive:
            return "sad"
        if positive > negative:
            return "positive"
        return "neutral"

    @classmethod
    def _contains_non_negated_term(cls, text: str, term: str) -> bool:
        if not cls._contains_term(text, term):
            return False
        negated = rf"(?<!\w)(?:not|no|never|without|tidak|bukan|tanpa)\s+(?:\w+\s+)?{re.escape(term)}(?!\w)"
        return not re.search(negated, text)

    @classmethod
    def _match_score(
        cls,
        profile: IntentProfile,
        text: str,
        themes: list[str],
        sentiment: str,
        language: str,
    ) -> float:
        score = 0.0
        if profile.mood and profile.mood.lower() in text:
            score += 0.2
        if profile.activity and profile.activity.lower() in text:
            score += 0.12
        if profile.genre and any(g.lower() in text for g in profile.genre):
            score += 0.12
        if profile.language == language:
            score += 0.08
        if profile.mood in {"sad", "melancholy", "galau"} and sentiment == "sad":
            score += 0.18
        if profile.energy == "high" and any(t in themes for t in ["party", "confidence"]):
            score += 0.12
        if profile.energy == "low" and any(t in themes for t in ["calm", "heartbreak", "longing"]):
            score += 0.12
        return round(max(0.0, min(1.0, score)), 4)

    @staticmethod
    def _summary(language: str, themes: list[str], sentiment: str, source_kind: str) -> str:
        if source_kind == "metadata_title_only":
            if language == "id":
                return "Metadata Genius tidak memuat deskripsi; makna lagu belum dapat dinilai."
            return "Genius metadata has no description; the song meaning cannot be assessed."
        theme_text = ", ".join(themes) if themes else "general song context"
        if language == "id":
            return f"Metadata Genius mengindikasikan tema {theme_text} dengan sentimen {sentiment}."
        return f"Genius metadata suggests {theme_text} themes with {sentiment} sentiment."
