from __future__ import annotations

import asyncio

import httpx
import pytest

from app.services.spotify_client import SpotifyClient


class _FakePlaylistClient:
    def __init__(self, add_status: int = 201) -> None:
        self.add_status = add_status

    async def get(self, url, **kwargs):
        return httpx.Response(
            200,
            json={"id": "user1"},
            request=httpx.Request("GET", url),
        )

    async def post(self, url, **kwargs):
        if url.endswith("/tracks"):
            return httpx.Response(
                self.add_status,
                json={"error": {"message": "cannot add tracks"}},
                request=httpx.Request("POST", url),
            )
        return httpx.Response(
            201,
            json={"id": "pl1", "external_urls": {"spotify": "https://open.spotify.com/playlist/pl1"}},
            request=httpx.Request("POST", url),
        )


def test_create_playlist_raises_when_add_tracks_fails() -> None:
    client = SpotifyClient()
    client.attach_client(_FakePlaylistClient(add_status=500))  # type: ignore[arg-type]

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(
            client.create_playlist(
                user_token="tok",
                title="Mix",
                description="auto",
                track_ids=["a", "b"],
            )
        )
