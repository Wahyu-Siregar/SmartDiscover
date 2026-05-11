from __future__ import annotations

import asyncio

import httpx

from app.models import IntentProfile, TrackCandidate
from app.services.genius_client import GeniusClient


class _FakeGeniusHttpClient:
    def __init__(self) -> None:
        self.urls: list[str] = []

    async def get(self, url, **kwargs):
        self.urls.append(url)
        if url.endswith("/search"):
            return httpx.Response(
                200,
                json={
                    "response": {
                        "hits": [
                            {
                                "result": {
                                    "id": 11,
                                    "title": "Rindu Berat",
                                    "full_title": "Rindu Berat by Sore",
                                    "url": "https://genius.com/sore-rindu-berat-lyrics",
                                    "primary_artist": {"name": "Sore"},
                                }
                            }
                        ]
                    }
                },
                request=httpx.Request("GET", url),
            )
        return httpx.Response(
            200,
            json={
                "response": {
                    "song": {
                        "lyrics_state": "complete",
                        "description_preview": "Lagu tentang rindu, kangen, dan patah hati.",
                    }
                }
            },
            request=httpx.Request("GET", url),
        )


def test_genius_enrich_candidates_adds_bounded_lyric_signals(monkeypatch) -> None:
    monkeypatch.setattr("app.services.genius_client.settings.genius_lyrics_enabled", True)
    monkeypatch.setattr("app.services.genius_client.settings.genius_access_token", "token")

    http_client = _FakeGeniusHttpClient()
    client = GeniusClient()
    client.attach_client(http_client)  # type: ignore[arg-type]
    candidates = [
        TrackCandidate(title="Rindu Berat", artist="Sore", track_id="1"),
        TrackCandidate(title="Tidak Diproses", artist="A", track_id="2"),
    ]

    info = asyncio.run(
        client.enrich_candidates(
            IntentProfile(mood="sad", energy="low", language="id"),
            candidates,
            limit=1,
        )
    )

    assert info["lookups"] == 1
    assert info["filled"] == 1
    assert candidates[0].lyric_signals is not None
    assert candidates[0].lyric_signals["source"] == "genius"
    assert "longing" in candidates[0].lyric_signals["themes"]
    assert candidates[1].lyric_signals is None
