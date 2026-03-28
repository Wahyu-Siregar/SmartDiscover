import time
from typing import Any

import httpx

import urllib.parse
from app.config import settings
from app.models import IntentProfile, TrackCandidate


class SpotifyClient:
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    SEARCH_URL = "https://api.spotify.com/v1/search"
    AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
    PROFILE_URL = "https://api.spotify.com/v1/me"

    LOCALE_TERMS = {
        "indonesia": ["indonesia", "indonesian", "nusantara", "tanah air", "merah putih", "garuda"],
    }

    def __init__(self) -> None:
        self._token: str = ""
        self._token_expiry: float = 0.0

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
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    self.SEARCH_URL,
                    params={"q": "focus", "type": "track", "limit": 1, "market": "ID"},
                    headers=headers,
                )
            if resp.status_code != 200:
                return {
                    "status": "spotify-error",
                    "ok": False,
                    "details": f"Spotify search failed with status {resp.status_code}.",
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

    async def search_tracks(self, profile: IntentProfile, target_count: int) -> tuple[list[TrackCandidate], dict[str, Any]]:
        if not settings.spotify_client_id or not settings.spotify_client_secret:
            return self._mock_tracks(profile, target_count), {
                "variants": [],
                "broadening_applied": False,
                "notes": "Spotify credentials belum diisi, menggunakan mock candidates untuk bootstrap development.",
            }

        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        candidates: dict[str, TrackCandidate] = {}
        
        # STRATEGI BARU: Cari playlist organik berdasarkan mood/aktivitas
        # Ini menghindari rekomendasi harfiah seperti judul lagu "melancholy"
        locale_suffix = f" {profile.locale}" if profile.locale else ""
        playlist_q = f"{profile.mood} {profile.activity}{locale_suffix}".strip()
        if not playlist_q and profile.genre:
            playlist_q = f"{profile.genre[0]}{locale_suffix}".strip()
            
        async with httpx.AsyncClient(timeout=20.0) as client:
            p_resp = await client.get(
                self.SEARCH_URL,
                params={"q": playlist_q, "type": "playlist", "limit": 3, "market": "ID"},
                headers=headers,
            )
            
            if p_resp.status_code == 200:
                playlists = p_resp.json().get("playlists", {}).get("items", [])
                for pl in playlists:
                    if not pl: continue
                    pl_id = pl.get("id")
                    
                    t_resp = await client.get(
                        f"https://api.spotify.com/v1/playlists/{pl_id}/tracks",
                        params={"limit": 15, "market": "ID"},
                        headers=headers,
                    )
                    if t_resp.status_code == 200:
                        items = t_resp.json().get("items", [])
                        for item in items:
                            track = item.get("track")
                            if track and track.get("id"):
                                candidates[track["id"]] = TrackCandidate(
                                    title=track.get("name", ""),
                                    artist=", ".join(a.get("name", "") for a in track.get("artists", [])),
                                    spotify_url=track.get("external_urls", {}).get("spotify", ""),
                                    preview_url=track.get("preview_url") or "",
                                    popularity=track.get("popularity", 0),
                                )

        broadening_applied = False
        variants = self._build_query_variants(profile)
        
        # FALLBACK / SUPPLEMENT: Jika track dari playlist terlalu sedikit
        if len(candidates) < target_count:
            broadening_applied = True
            for q in variants:
                params = {
                    "q": q,
                    "type": "track",
                    "limit": min(10, max(5, target_count // 3)),
                    "market": "ID",
                }
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(self.SEARCH_URL, params=params, headers=headers)
                if resp.status_code == 200:
                    items = resp.json().get("tracks", {}).get("items", [])
                    for item in items:
                        if item.get("id") and item["id"] not in candidates:
                            candidates[item["id"]] = TrackCandidate(
                                title=item.get("name", ""),
                                artist=", ".join(a.get("name", "") for a in item.get("artists", [])),
                                spotify_url=item.get("external_urls", {}).get("spotify", ""),
                                preview_url=item.get("preview_url") or "",
                                popularity=item.get("popularity", 0),
                            )

        final_candidates = list(candidates.values())
        strict_filtered_count = 0
        if profile.locale and profile.strict_locale:
            filtered = self._filter_by_locale(final_candidates, profile.locale)
            # Keep strict mode only if still have enough reasonable candidates.
            min_keep = max(5, min(target_count, 10))
            if len(filtered) >= min_keep:
                strict_filtered_count = len(final_candidates) - len(filtered)
                final_candidates = filtered

        return final_candidates, {
            "variants": [playlist_q] + variants,
            "broadening_applied": broadening_applied,
            "notes": "Pencarian diutamakan via playlist organik untuk koleksi genre/mood yang kaya, lalu fallback ke pencarian track biasa.",
            "locale": profile.locale,
            "strict_locale": profile.strict_locale,
            "strict_filtered_count": strict_filtered_count,
        }

    async def _get_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry:
            return self._token

        data = {"grant_type": "client_credentials"}
        auth = (settings.spotify_client_id, settings.spotify_client_secret)
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(self.TOKEN_URL, data=data, auth=auth)

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
        if profile.locale:
            base.append(f"{profile.locale} patriotic songs")
            base.append(f"{profile.locale} national songs")
        # Keep variants unique while preserving order.
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

    def get_authorization_url(self, redirect_uri: str) -> str:
        params = {
            "client_id": settings.spotify_client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "playlist-modify-public playlist-modify-private",
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
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(self.TOKEN_URL, data=data, auth=auth)
        resp.raise_for_status()
        return resp.json()

    async def create_playlist(
        self, user_token: str, title: str, description: str, track_ids: list[str]
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {user_token}"}
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            profile_resp = await client.get(self.PROFILE_URL, headers=headers)
            profile_resp.raise_for_status()
            user_id = profile_resp.json()["id"]

            create_payload = {"name": title, "description": description, "public": False}
            create_url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
            create_resp = await client.post(create_url, json=create_payload, headers=headers)
            create_resp.raise_for_status()
            
            playlist_data = create_resp.json()
            playlist_id = playlist_data["id"]

            if track_ids:
                uris = [f"spotify:track:{tid}" for tid in track_ids]
                add_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
                await client.post(add_url, json={"uris": uris}, headers=headers)

            return {"id": playlist_id, "url": playlist_data["external_urls"]["spotify"]}
