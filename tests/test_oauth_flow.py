"""OAuth flow regression tests: state CSRF, cookie session, status endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    # Disable redirect following so we can inspect /auth/login redirect.
    return TestClient(app, follow_redirects=False)


def test_login_sets_state_cookie_and_redirects_to_spotify(monkeypatch) -> None:
    monkeypatch.setattr("app.config.settings.spotify_client_id", "test-client")
    client = _client()
    resp = client.get("/auth/login")
    assert resp.status_code in (302, 307)

    location = resp.headers["location"]
    assert location.startswith("https://accounts.spotify.com/authorize")
    assert "state=" in location

    # The signed state cookie must be set HttpOnly.
    set_cookie = resp.headers.get("set-cookie", "")
    assert "sd_oauth_state=" in set_cookie
    assert "httponly" in set_cookie.lower()


def test_callback_rejects_state_mismatch(monkeypatch) -> None:
    client = _client()
    # First obtain a valid state cookie via /auth/login.
    login = client.get("/auth/login")
    cookies = login.cookies

    # Forge a wrong state.
    resp = client.get(
        "/auth/callback",
        params={"code": "abc", "state": "tampered"},
        cookies=cookies,
    )
    assert resp.status_code == 400


def test_callback_rejects_missing_state_cookie() -> None:
    client = _client()
    resp = client.get("/auth/callback", params={"code": "abc", "state": "anything"})
    assert resp.status_code == 400


def test_auth_status_default_disconnected() -> None:
    client = _client()
    resp = client.get("/auth/status")
    assert resp.status_code == 200
    assert resp.json() == {"connected": False}


def test_callback_happy_path_sets_session_cookie(monkeypatch) -> None:
    async def fake_get_user_token(self, code: str, redirect_uri: str):
        assert code == "real-code"
        return {
            "access_token": "spotify-access",
            "refresh_token": "spotify-refresh",
            "expires_in": 3600,
        }

    monkeypatch.setattr(
        "app.services.spotify_client.SpotifyClient.get_user_token",
        fake_get_user_token,
    )

    client = _client()
    login = client.get("/auth/login")
    state_cookie = login.cookies.get("sd_oauth_state")
    # Extract the unsigned nonce by re-using the serializer.
    from app.main import _oauth_state_serializer
    nonce = _oauth_state_serializer.loads(state_cookie)

    resp = client.get(
        "/auth/callback",
        params={"code": "real-code", "state": nonce},
        cookies={"sd_oauth_state": state_cookie},
    )
    assert resp.status_code in (302, 307)
    set_cookie = resp.headers.get("set-cookie", "")
    assert "sd_session=" in set_cookie
    assert "httponly" in set_cookie.lower()

    # /auth/status should now report connected when the session cookie is presented.
    session_cookie_value = resp.cookies.get("sd_session")
    assert session_cookie_value
    status_resp = client.get("/auth/status", cookies={"sd_session": session_cookie_value})
    assert status_resp.status_code == 200
    assert status_resp.json()["connected"] is True
