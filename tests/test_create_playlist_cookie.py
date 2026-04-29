"""/create-playlist must require a valid HttpOnly session cookie, not a body token."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import _session_serializer, app


client = TestClient(app)


def _make_session_cookie(access_token: str = "tok", expires_in: int = 3600) -> str:
    return _session_serializer.dumps(
        {
            "access_token": access_token,
            "refresh_token": "",
            "expires_at": time.time() + expires_in,
        }
    )


def test_create_playlist_unauthorized_without_cookie() -> None:
    resp = client.post(
        "/create-playlist",
        json={"title": "Test", "description": "", "track_ids": []},
    )
    assert resp.status_code == 401


def test_create_playlist_rejects_legacy_user_token_field() -> None:
    # Legacy clients sending user_token in body must still fail without a cookie.
    resp = client.post(
        "/create-playlist",
        json={
            "user_token": "legacy",
            "title": "Test",
            "description": "",
            "track_ids": [],
        },
    )
    assert resp.status_code == 401


def test_create_playlist_with_valid_session(monkeypatch) -> None:
    captured: dict = {}

    async def fake_create_playlist(self, *, user_token, title, description, track_ids):
        captured.update(
            {"user_token": user_token, "title": title, "track_ids": track_ids}
        )
        return {"id": "pl1", "url": "https://open.spotify.com/playlist/pl1"}

    monkeypatch.setattr(
        "app.services.spotify_client.SpotifyClient.create_playlist",
        fake_create_playlist,
    )

    cookie = _make_session_cookie(access_token="from-cookie")
    resp = client.post(
        "/create-playlist",
        json={"title": "Mix", "description": "auto", "track_ids": ["a", "b"]},
        cookies={"sd_session": cookie},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "pl1"
    assert captured["user_token"] == "from-cookie"
    assert captured["track_ids"] == ["a", "b"]


def test_create_playlist_expired_session_returns_401() -> None:
    expired = _session_serializer.dumps(
        {
            "access_token": "tok",
            "refresh_token": "",
            "expires_at": time.time() - 60,
        }
    )
    resp = client.post(
        "/create-playlist",
        json={"title": "Mix", "description": "", "track_ids": []},
        cookies={"sd_session": expired},
    )
    assert resp.status_code == 401
