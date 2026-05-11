import asyncio
import re
from typing import Any

import httpx

from app.config import settings
from app.models import IntentProfile, TrackCandidate
from app.services.cache import TTLCache


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

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
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
        signals = await asyncio.gather(
            *[self.lookup_track(profile, track) for track in selected],
            return_exceptions=True,
        )

        filled = 0
        for track, signal in zip(selected, signals):
            if isinstance(signal, Exception) or not signal:
                continue
            track.lyric_signals = signal
            filled += 1

        return {"enabled": True, "lookups": safe_limit, "filled": filled, "source": "genius"}

    async def lookup_track(self, profile: IntentProfile, track: TrackCandidate) -> dict[str, Any] | None:
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
                self._cache.set(key, None)
                return None
            hit = self._best_hit(track, search_resp.json().get("response", {}).get("hits", []) or [])
            if not hit:
                self._cache.set(key, None)
                return None

            result = hit.get("result", {}) or {}
            song = await self._fetch_song(result.get("id"))
            signal = self._build_signal(profile, track, result, song)
            self._cache.set(key, signal)
            return signal
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
        title = str(result.get("title") or track.title)
        artist = str((result.get("primary_artist") or {}).get("name") or track.artist)
        description = str(song.get("description_preview") or result.get("full_title") or "")
        text = self._normalize_text(f"{title} {artist} {description}")
        themes = self._themes(text)
        sentiment = self._sentiment(text)
        language = "id" if any(word in text for word in ID_WORDS) else profile.language
        match_score = self._match_score(profile, text, themes, sentiment, language)

        return {
            "source": "genius",
            "source_url": result.get("url") or song.get("url") or "",
            "lyrics_state": song.get("lyrics_state") or result.get("lyrics_state") or "unknown",
            "language": language,
            "themes": themes,
            "sentiment": sentiment,
            "summary": self._summary(language, themes, sentiment),
            "match_score": match_score,
            "note": "Genius API metadata signal; full lyrics are not returned by the official API.",
        }

    @staticmethod
    def _cache_key(track: TrackCandidate) -> str:
        if track.track_id:
            return f"spotify::{track.track_id}"
        return f"name::{track.title.lower()}::{track.artist.lower()}"

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
            if title and (title in hit_title or hit_title in title) and artist and artist in hit_artist:
                return hit
        return hits[0]

    @staticmethod
    def _themes(text: str) -> list[str]:
        themes = [theme for theme, words in THEME_KEYWORDS.items() if any(word in text for word in words)]
        return themes[:4]

    @staticmethod
    def _sentiment(text: str) -> str:
        negative = sum(1 for word in NEGATIVE_WORDS if word in text)
        positive = sum(1 for word in POSITIVE_WORDS if word in text)
        if negative > positive:
            return "sad"
        if positive > negative:
            return "positive"
        return "neutral"

    @staticmethod
    def _match_score(
        profile: IntentProfile,
        text: str,
        themes: list[str],
        sentiment: str,
        language: str,
    ) -> float:
        score = 0.35
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
    def _summary(language: str, themes: list[str], sentiment: str) -> str:
        theme_text = ", ".join(themes) if themes else "general song context"
        if language == "id":
            return f"Sinyal Genius menunjukkan tema {theme_text} dengan sentimen {sentiment}."
        return f"Genius signals suggest {theme_text} themes with {sentiment} sentiment."
