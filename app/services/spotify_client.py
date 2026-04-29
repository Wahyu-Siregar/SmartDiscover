import asyncio
import json
import re
import time
import urllib.parse
from typing import Any

import httpx
from tenacity import AsyncRetrying, RetryError, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.config import settings
from app.models import IntentProfile, TrackCandidate


_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class _RetryableHTTPError(Exception):
    pass


# Locale to Spotify ISO market code (uppercase 2-letter).
LOCALE_TO_MARKET = {
    "indonesia": "ID",
    "malaysia": "MY",
    "singapore": "SG",
    "philippines": "PH",
    "thailand": "TH",
    "vietnam": "VN",
    "japan": "JP",
    "korea": "KR",
    "united states": "US",
    "usa": "US",
    "us": "US",
    "uk": "GB",
    "united kingdom": "GB",
}


class SpotifyClient:
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    SEARCH_URL = "https://api.spotify.com/v1/search"
    AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
    PROFILE_URL = "https://api.spotify.com/v1/me"
    EMBED_TRACK_URL = "https://open.spotify.com/embed/track/{track_id}"
    EMBED_PREVIEW_MAX_LOOKUPS = 10

    LOCALE_TERMS = {
        "indonesia": ["indonesia", "indonesian", "nusantara", "tanah air", "merah putih", "garuda"],
    }

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._token: str = ""
        self._token_expiry: float = 0.0
        self._client = client

    def attach_client(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("SpotifyClient.attach_client() must be called before use")
        return self._client

    def resolve_market(self, profile: IntentProfile) -> str:
        if profile.locale:
            mapped = LOCALE_TO_MARKET.get(profile.locale.strip().lower())
            if mapped:
                return mapped
        return settings.spotify_default_market or "ID"

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: Any = None,
        json_body: Any = None,
        auth: tuple[str, str] | None = None,
        timeout: float = 20.0,
    ) -> httpx.Response | None:
        client = self._require_client()

        async def _do() -> httpx.Response:
            resp = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                data=data,
                json=json_body,
                auth=auth,
                timeout=timeout,
            )
            if resp.status_code in _RETRYABLE_STATUSES:
                raise _RetryableHTTPError(f"{method} {url} -> {resp.status_code}")
            return resp

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential_jitter(initial=0.4, max=2.0),
                retry=retry_if_exception_type((_RetryableHTTPError, httpx.TransportError, httpx.TimeoutException)),
                reraise=False,
            ):
                with attempt:
                    return await _do()
        except RetryError:
            return None
        except Exception:
            return None
        return None

    async def health_check(self) -> dict[str, Any]:
        if not settings.spotify_client_id or not settings.spotify_client_secret:
            return {
                "status": "mock-mode",
                "ok": True,
                "details": "Spotify credentials belum diisi.",
            }

        try:
            token = await self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            resp = await self._request_with_retry(
                "GET",
                self.SEARCH_URL,
                params={"q": "focus", "type": "track", "limit": 1, "market": settings.spotify_default_market or "ID"},
                headers=headers,
            )
            if resp is None or resp.status_code != 200:
                code = resp.status_code if resp is not None else "n/a"
                return {
                    "status": "spotify-error",
                    "ok": False,
                    "details": f"Spotify search failed with status {code}.",
                }
            total = resp.json().get("tracks", {}).get("total", 0)
            return {
                "status": "ok",
                "ok": True,
                "details": f"Spotify reachable, total sample tracks: {total}.",
            }
        except Exception as exc:
            return {
                "status": "spotify-exception",
                "ok": False,
                "details": str(exc),
            }

    async def search_tracks(
        self, profile: IntentProfile, target_count: int
    ) -> tuple[list[TrackCandidate], dict[str, Any]]:
        if not settings.spotify_client_id or not settings.spotify_client_secret:
            return self._mock_tracks(profile, target_count), {
                "variants": [],
                "broadening_applied": False,
                "notes": "Spotify credentials belum diisi, menggunakan mock candidates untuk bootstrap development.",
            }

        market = self.resolve_market(profile)
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        candidates: dict[str, TrackCandidate] = {}

        # STRATEGI: Cari playlist organik berdasarkan intent utama.
        locale_suffix = f" {profile.locale}" if profile.locale else ""
        explicit_genre_only = bool(profile.genre) and profile.mood == "neutral" and profile.activity == "listening"
        if explicit_genre_only:
            base_q = f"lagu {profile.genre[0]}" if profile.language == "id" else f"{profile.genre[0]} songs"
            playlist_q = f"{base_q.strip()}{locale_suffix}".strip()
        else:
            playlist_q = f"{profile.mood} {profile.activity}{locale_suffix}".strip()
            if not playlist_q.strip() and profile.genre:
                playlist_q = f"{profile.genre[0]}{locale_suffix}".strip()

        p_resp = await self._request_with_retry(
            "GET",
            self.SEARCH_URL,
            params={"q": playlist_q, "type": "playlist", "limit": 3, "market": market},
            headers=headers,
        )

        if p_resp is not None and p_resp.status_code == 200:
            playlists = p_resp.json().get("playlists", {}).get("items", [])
            playlist_ids = [pl.get("id") for pl in playlists if pl and pl.get("id")]

            # Parallel fetch of all playlist tracks.
            track_tasks = [
                self._request_with_retry(
                    "GET",
                    f"https://api.spotify.com/v1/playlists/{pl_id}/tracks",
                    params={"limit": 15, "market": market},
                    headers=headers,
                )
                for pl_id in playlist_ids
            ]
            track_responses = await asyncio.gather(*track_tasks, return_exceptions=True)

            for resp in track_responses:
                if isinstance(resp, Exception) or resp is None or resp.status_code != 200:
                    continue
                items = resp.json().get("items", [])
                for item in items:
                    track = item.get("track")
                    if track and track.get("id") and track["id"] not in candidates:
                        candidates[track["id"]] = TrackCandidate(
                            title=track.get("name", ""),
                            artist=", ".join(a.get("name", "") for a in track.get("artists", [])),
                            track_id=track["id"],
                            spotify_url=track.get("external_urls", {}).get("spotify", ""),
                            preview_url=track.get("preview_url") or "",
                            popularity=track.get("popularity", 0),
                            artist_ids=[a.get("id", "") for a in track.get("artists", []) if a.get("id")],
                        )

        broadening_applied = False
        variants = self._build_query_variants(profile)

        # FALLBACK / SUPPLEMENT: parallel variant searches when shortfall.
        if len(candidates) < target_count and variants:
            broadening_applied = True
            limit_per_variant = min(10, max(5, target_count // 3))
            variant_tasks = [
                self._request_with_retry(
                    "GET",
                    self.SEARCH_URL,
                    params={"q": q, "type": "track", "limit": limit_per_variant, "market": market},
                    headers=headers,
                )
                for q in variants
            ]
            variant_responses = await asyncio.gather(*variant_tasks, return_exceptions=True)

            for resp in variant_responses:
                if isinstance(resp, Exception) or resp is None or resp.status_code != 200:
                    continue
                items = resp.json().get("tracks", {}).get("items", [])
                for item in items:
                    if item.get("id") and item["id"] not in candidates:
                        candidates[item["id"]] = TrackCandidate(
                            title=item.get("name", ""),
                            artist=", ".join(a.get("name", "") for a in item.get("artists", [])),
                            track_id=item["id"],
                            spotify_url=item.get("external_urls", {}).get("spotify", ""),
                            preview_url=item.get("preview_url") or "",
                            popularity=item.get("popularity", 0),
                            artist_ids=[a.get("id", "") for a in item.get("artists", []) if a.get("id")],
                        )

        preview_fallback_count = await self._enrich_missing_previews(candidates, target_count)
        final_candidates = list(candidates.values())
        strict_filtered_count = 0
        if profile.locale and profile.strict_locale:
            filtered = self._filter_by_locale(final_candidates, profile.locale)
            min_keep = max(5, min(target_count, 10))
            if len(filtered) >= min_keep:
                strict_filtered_count = len(final_candidates) - len(filtered)
                final_candidates = filtered

        return final_candidates, {
            "variants": [playlist_q] + variants,
            "broadening_applied": broadening_applied,
            "notes": "Pencarian diutamakan via playlist organik untuk koleksi genre/mood yang kaya, lalu fallback ke pencarian track biasa.",
            "locale": profile.locale,
            "market": market,
            "strict_locale": profile.strict_locale,
            "strict_filtered_count": strict_filtered_count,
            "preview_fallback_count": preview_fallback_count,
        }

    async def _enrich_missing_previews(
        self, candidates: dict[str, TrackCandidate], target_count: int
    ) -> int:
        missing_track_ids = [tid for tid, c in candidates.items() if not c.preview_url]
        if not missing_track_ids:
            return 0

        lookup_limit = min(self.EMBED_PREVIEW_MAX_LOOKUPS, max(4, target_count * 2))
        lookup_ids = missing_track_ids[:lookup_limit]

        # Embed scraping uses the shared client too (open.spotify.com).
        tasks = [self._fetch_preview_from_embed(track_id) for track_id in lookup_ids]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        filled = 0
        for track_id, preview_url in zip(lookup_ids, responses):
            if isinstance(preview_url, Exception) or not isinstance(preview_url, str) or not preview_url:
                continue
            candidate = candidates.get(track_id)
            if candidate and not candidate.preview_url:
                candidate.preview_url = preview_url
                filled += 1
        return filled

    async def _fetch_preview_from_embed(self, track_id: str) -> str | None:
        try:
            client = self._require_client()
            url = self.EMBED_TRACK_URL.format(track_id=track_id)
            response = await client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": "SmartDiscover/1.0"},
                timeout=10.0,
            )
            if response.status_code != 200:
                return None
            return self._extract_preview_from_embed_html(response.text)
        except Exception:
            return None

    @staticmethod
    def _extract_preview_from_embed_html(html: str) -> str | None:
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not match:
            return None
        try:
            json_data = json.loads(match.group(1))
        except Exception:
            return None
        audio_preview = (
            json_data.get("props", {})
            .get("pageProps", {})
            .get("state", {})
            .get("data", {})
            .get("entity", {})
            .get("audioPreview", {})
            .get("url")
        )
        return audio_preview if isinstance(audio_preview, str) and audio_preview else None

    async def _get_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry:
            return self._token

        data = {"grant_type": "client_credentials"}
        auth = (settings.spotify_client_id, settings.spotify_client_secret)
        resp = await self._request_with_retry("POST", self.TOKEN_URL, data=data, auth=auth)
        if resp is None:
            raise RuntimeError("Spotify token request failed")
        resp.raise_for_status()
        body = resp.json()
        self._token = body["access_token"]
        self._token_expiry = now + int(body.get("expires_in", 3600)) - 60
        return self._token

    def _build_query_variants(self, profile: IntentProfile) -> list[str]:
        genres = profile.genre or ["music"]
        locale_suffix = f" {profile.locale}" if profile.locale else ""
        base = [
            f"{profile.mood} {profile.activity}{locale_suffix}",
            f"{profile.activity} {profile.energy}{locale_suffix}",
            f"{profile.mood} playlist{locale_suffix}",
        ]
        base.extend(f"{g} {profile.activity}{locale_suffix}" for g in genres[:3])
        base.extend(f"{g} songs{locale_suffix}" for g in genres[:3])
        if profile.language == "id":
            base.extend(f"lagu {g}{locale_suffix}" for g in genres[:3])
        if profile.locale:
            base.append(f"{profile.locale} patriotic songs")
            base.append(f"{profile.locale} national songs")
        return list(dict.fromkeys(base))[:6]

    def _filter_by_locale(self, candidates: list[TrackCandidate], locale: str) -> list[TrackCandidate]:
        terms = self.LOCALE_TERMS.get(locale.lower(), [])
        if not terms:
            return candidates

        def matches_locale(candidate: TrackCandidate) -> bool:
            text = f"{candidate.title} {candidate.artist}".lower()
            return any(term in text for term in terms)

        return [c for c in candidates if matches_locale(c)]

    def _mock_tracks(self, profile: IntentProfile, target_count: int) -> list[TrackCandidate]:
        seed = [
            ("Midnight Focus", "Loftline"),
            ("Rainy Notes", "Ambaris"),
            ("Quiet Orbit", "Nexa Tone"),
            ("Paper and Coffee", "Sore Hari"),
            ("Blue Window", "Tala River"),
            ("Gentle Pulse", "Mono Atelier"),
            ("City at 2AM", "Sleepwalker Unit"),
            ("Clouded Desk", "Lentera"),
            ("Far Lamp", "North Avenue"),
            ("After Class", "Nadi Muda"),
            ("Nocturnal Study", "Pilot Frames"),
            ("Ambient Roof", "Sky Thread"),
            ("Warm Neon", "Satelit"),
            ("Soft Sprint", "Morning Gear"),
            ("Slow Horizon", "Kroma"),
            ("Paper Crane", "Aster"),
            ("Evening Byte", "Delta Echo"),
            ("Static Bloom", "Ruang Nada"),
            ("Northbound", "June Atlas"),
            ("Quiet Street", "Rinai"),
        ]

        items: list[TrackCandidate] = []
        for i, (title, artist) in enumerate(seed[: max(target_count + 5, 20)]):
            items.append(
                TrackCandidate(
                    title=title,
                    artist=artist,
                    spotify_url="",
                    preview_url="",
                    popularity=max(10, 100 - (i * 4)),
                    score=0.0,
                )
            )
        return items

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": settings.spotify_client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "playlist-modify-public playlist-modify-private",
            "state": state,
        }
        query = urllib.parse.urlencode(params)
        return f"{self.AUTHORIZE_URL}?{query}"

    async def get_user_token(self, code: str, redirect_uri: str) -> dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
        auth = (settings.spotify_client_id, settings.spotify_client_secret)
        resp = await self._request_with_retry("POST", self.TOKEN_URL, data=data, auth=auth)
        if resp is None:
            raise RuntimeError("Spotify token exchange failed")
        resp.raise_for_status()
        return resp.json()

    async def refresh_user_token(self, refresh_token: str) -> dict[str, Any]:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        auth = (settings.spotify_client_id, settings.spotify_client_secret)
        resp = await self._request_with_retry("POST", self.TOKEN_URL, data=data, auth=auth)
        if resp is None:
            raise RuntimeError("Spotify token refresh failed")
        resp.raise_for_status()
        return resp.json()

    # ---- Audio features / artists / recommendations -------------------

    AUDIO_FEATURES_URL = "https://api.spotify.com/v1/audio-features"
    ARTISTS_URL = "https://api.spotify.com/v1/artists"
    RECOMMENDATIONS_URL = "https://api.spotify.com/v1/recommendations"
    AVAILABLE_GENRE_SEEDS_URL = "https://api.spotify.com/v1/recommendations/available-genre-seeds"

    _AUDIO_FEATURE_KEYS = (
        "tempo",
        "energy",
        "valence",
        "danceability",
        "acousticness",
        "instrumentalness",
        "loudness",
    )

    async def get_audio_features(self, track_ids: list[str]) -> dict[str, dict[str, float]]:
        """Batch fetch audio features. Returns map of track_id -> feature dict."""
        if not track_ids:
            return {}
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        async def _batch(ids: list[str]) -> list[dict | None]:
            resp = await self._request_with_retry(
                "GET",
                self.AUDIO_FEATURES_URL,
                params={"ids": ",".join(ids)},
                headers=headers,
            )
            if resp is None or resp.status_code != 200:
                return [None] * len(ids)
            data = resp.json().get("audio_features", []) or []
            # Spotify returns nulls for missing tracks; normalize length.
            if len(data) < len(ids):
                data = list(data) + [None] * (len(ids) - len(data))
            return data

        chunks = [track_ids[i : i + 100] for i in range(0, len(track_ids), 100)]
        results = await asyncio.gather(*[_batch(c) for c in chunks])

        out: dict[str, dict[str, float]] = {}
        flat: list[dict | None] = [item for sub in results for item in sub]
        for tid, feat in zip(track_ids, flat):
            if not feat:
                continue
            out[tid] = {k: float(feat[k]) for k in self._AUDIO_FEATURE_KEYS if k in feat and feat[k] is not None}
        return out

    async def get_artists(self, artist_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Batch fetch artists. Returns map of artist_id -> {name, genres}."""
        unique = list(dict.fromkeys([a for a in artist_ids if a]))
        if not unique:
            return {}
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        async def _batch(ids: list[str]) -> list[dict]:
            resp = await self._request_with_retry(
                "GET",
                self.ARTISTS_URL,
                params={"ids": ",".join(ids)},
                headers=headers,
            )
            if resp is None or resp.status_code != 200:
                return []
            return resp.json().get("artists", []) or []

        chunks = [unique[i : i + 50] for i in range(0, len(unique), 50)]
        results = await asyncio.gather(*[_batch(c) for c in chunks])

        out: dict[str, dict[str, Any]] = {}
        for arts in results:
            for a in arts:
                if a and a.get("id"):
                    out[a["id"]] = {
                        "name": a.get("name", ""),
                        "genres": list(a.get("genres", []) or []),
                    }
        return out

    async def get_available_genre_seeds(self) -> list[str]:
        if hasattr(self, "_genre_seed_cache") and self._genre_seed_cache is not None:
            return self._genre_seed_cache
        try:
            token = await self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            resp = await self._request_with_retry(
                "GET",
                self.AVAILABLE_GENRE_SEEDS_URL,
                headers=headers,
            )
            if resp is None or resp.status_code != 200:
                self._genre_seed_cache = []
                return []
            seeds = list(resp.json().get("genres", []) or [])
            self._genre_seed_cache = seeds
            return seeds
        except Exception:
            self._genre_seed_cache = []
            return []

    async def get_recommendations(
        self,
        *,
        seed_genres: list[str] | None = None,
        seed_artists: list[str] | None = None,
        seed_tracks: list[str] | None = None,
        target_audio: dict[str, float] | None = None,
        market: str | None = None,
        limit: int = 50,
    ) -> list[TrackCandidate]:
        """Spotify Recommendations endpoint. Returns TrackCandidate list (no audio features yet)."""
        seeds: dict[str, str] = {}
        if seed_genres:
            seeds["seed_genres"] = ",".join(seed_genres[:5])
        if seed_artists:
            seeds["seed_artists"] = ",".join(seed_artists[:5])
        if seed_tracks:
            seeds["seed_tracks"] = ",".join(seed_tracks[:5])
        if not seeds:
            return []

        params: dict[str, Any] = dict(seeds)
        params["limit"] = max(1, min(100, limit))
        if market:
            params["market"] = market
        if target_audio:
            for key, value in target_audio.items():
                if value is None:
                    continue
                if key in {"energy", "valence", "danceability", "acousticness", "instrumentalness"}:
                    params[f"target_{key}"] = max(0.0, min(1.0, float(value)))
                elif key == "tempo":
                    params["target_tempo"] = float(value)
                elif key == "popularity":
                    params["target_popularity"] = int(max(0, min(100, value)))

        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = await self._request_with_retry(
            "GET",
            self.RECOMMENDATIONS_URL,
            params=params,
            headers=headers,
        )
        if resp is None or resp.status_code != 200:
            return []

        items = resp.json().get("tracks", []) or []
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
        return out

    async def gather_candidates(
        self, profile: IntentProfile, target_count: int
    ) -> tuple[list[TrackCandidate], dict[str, Any]]:
        """Unified candidate gathering: recommendations first, supplement via search, then enrich."""
        if not settings.spotify_client_id or not settings.spotify_client_secret:
            return self._mock_tracks(profile, target_count), {
                "variants": [],
                "broadening_applied": False,
                "used_recommendations": False,
                "notes": "Spotify credentials belum diisi, menggunakan mock candidates.",
            }

        market = self.resolve_market(profile)
        used_recommendations = False
        candidates: dict[str, TrackCandidate] = {}
        recs_strategy: dict[str, Any] = {}

        # 1) Try recommendations endpoint when we have valid seed_genres.
        if profile.seed_genres:
            available = await self.get_available_genre_seeds()
            valid_seeds = (
                [g for g in profile.seed_genres if g in available]
                if available
                else list(profile.seed_genres)
            )
            if valid_seeds:
                recs = await self.get_recommendations(
                    seed_genres=valid_seeds,
                    target_audio=profile.target_audio or {},
                    market=market,
                    limit=min(100, max(target_count * 3, 30)),
                )
                if recs:
                    used_recommendations = True
                    for c in recs:
                        if c.track_id and c.track_id not in candidates:
                            candidates[c.track_id] = c
                recs_strategy = {
                    "seed_genres": valid_seeds,
                    "target_audio": profile.target_audio,
                }

        # 2) Supplement via existing playlist+search flow if shortfall.
        playlist_strategy: dict[str, Any] = {}
        broadening_applied = False
        if len(candidates) < target_count * 2:
            extras, playlist_strategy = await self.search_tracks(profile, target_count)
            broadening_applied = bool(playlist_strategy.get("broadening_applied"))
            for c in extras:
                if c.track_id and c.track_id not in candidates:
                    candidates[c.track_id] = c
                elif not c.track_id:
                    # Mock or partial entries without ID; keep with synthetic key.
                    candidates[f"_no_id_{len(candidates)}"] = c

        final_candidates = list(candidates.values())

        # 3) Enrich with audio features + artist genres in parallel.
        track_ids = [c.track_id for c in final_candidates if c.track_id]
        artist_ids = [aid for c in final_candidates for aid in c.artist_ids]
        try:
            features_map, artists_map = await asyncio.gather(
                self.get_audio_features(track_ids),
                self.get_artists(artist_ids),
            )
        except Exception:
            features_map, artists_map = {}, {}

        for c in final_candidates:
            if c.track_id and c.track_id in features_map:
                c.audio_features = features_map[c.track_id]
            if c.artist_ids:
                merged_genres: list[str] = []
                for aid in c.artist_ids:
                    info = artists_map.get(aid)
                    if info:
                        for g in info.get("genres", []):
                            if g not in merged_genres:
                                merged_genres.append(g)
                if merged_genres:
                    c.genres = merged_genres

        # 4) Strict locale filtering retained.
        strict_filtered_count = 0
        if profile.locale and profile.strict_locale:
            filtered = self._filter_by_locale(final_candidates, profile.locale)
            min_keep = max(5, min(target_count, 10))
            if len(filtered) >= min_keep:
                strict_filtered_count = len(final_candidates) - len(filtered)
                final_candidates = filtered

        return final_candidates, {
            "used_recommendations": used_recommendations,
            "recommendations_strategy": recs_strategy,
            "playlist_strategy": playlist_strategy,
            "broadening_applied": broadening_applied,
            "locale": profile.locale,
            "market": market,
            "strict_locale": profile.strict_locale,
            "strict_filtered_count": strict_filtered_count,
            "audio_features_filled": sum(1 for c in final_candidates if c.audio_features),
            "artist_genres_filled": sum(1 for c in final_candidates if c.genres),
        }

    async def create_playlist(
        self, user_token: str, title: str, description: str, track_ids: list[str]
    ) -> dict[str, Any]:
        client = self._require_client()
        headers = {"Authorization": f"Bearer {user_token}"}

        profile_resp = await client.get(self.PROFILE_URL, headers=headers, timeout=20.0)
        profile_resp.raise_for_status()
        user_id = profile_resp.json()["id"]

        create_payload = {"name": title, "description": description, "public": False}
        create_url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
        create_resp = await client.post(create_url, json=create_payload, headers=headers, timeout=20.0)
        create_resp.raise_for_status()

        playlist_data = create_resp.json()
        playlist_id = playlist_data["id"]

        if track_ids:
            uris = [f"spotify:track:{tid}" for tid in track_ids]
            add_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
            await client.post(add_url, json={"uris": uris}, headers=headers, timeout=20.0)

        return {"id": playlist_id, "url": playlist_data["external_urls"]["spotify"]}
