"""Audio features and artist genres get attached during gather_candidates enrichment."""
from __future__ import annotations

import asyncio
from typing import Any

from app.models import IntentProfile, TrackCandidate
from app.services.spotify_client import SpotifyClient


class _FakeAsyncClient:
    """Stand-in for httpx.AsyncClient to satisfy `_require_client()`."""


def _setup(monkeypatch) -> SpotifyClient:
    client = SpotifyClient()
    client.attach_client(_FakeAsyncClient())  # type: ignore[arg-type]

    monkeypatch.setattr("app.services.spotify_client.settings.spotify_client_id", "x")
    monkeypatch.setattr("app.services.spotify_client.settings.spotify_client_secret", "y")
    monkeypatch.setattr("app.services.spotify_client.settings.spotify_default_market", "ID")

    async def fake_token() -> str:
        return "fake-token"

    monkeypatch.setattr(client, "_get_access_token", fake_token, raising=False)
    return client


def test_gather_candidates_enriches_audio_and_genres(monkeypatch) -> None:
    client = _setup(monkeypatch)

    # Pre-built candidates returned by search_tracks (skip recommendations path).
    seed_candidates = [
        TrackCandidate(
            title="A", artist="Artist X", track_id="tid_a", artist_ids=["aid_x"], popularity=70
        ),
        TrackCandidate(
            title="B", artist="Artist Y", track_id="tid_b", artist_ids=["aid_y"], popularity=60
        ),
    ]

    async def fake_search(profile, target_count):
        return list(seed_candidates), {"variants": [], "broadening_applied": False}

    async def fake_audio(track_ids: list[str]) -> dict[str, dict[str, float]]:
        return {
            "tid_a": {"energy": 0.8, "valence": 0.6, "tempo": 120.0},
            "tid_b": {"energy": 0.3, "valence": 0.4, "tempo": 90.0},
        }

    async def fake_artists(artist_ids: list[str]) -> dict[str, dict[str, Any]]:
        return {
            "aid_x": {"name": "Artist X", "genres": ["indie pop", "bedroom pop"]},
            "aid_y": {"name": "Artist Y", "genres": ["jazz"]},
        }

    monkeypatch.setattr(client, "search_tracks", fake_search, raising=False)
    monkeypatch.setattr(client, "get_audio_features", fake_audio, raising=False)
    monkeypatch.setattr(client, "get_artists", fake_artists, raising=False)

    # Profile without seed_genres -> recommendations branch is skipped.
    profile = IntentProfile(mood="happy", activity="listening", language="en")

    candidates, strategy = asyncio.run(client.gather_candidates(profile, target_count=10))

    assert len(candidates) == 2
    by_id = {c.track_id: c for c in candidates}
    assert by_id["tid_a"].audio_features == {"energy": 0.8, "valence": 0.6, "tempo": 120.0}
    assert "indie pop" in by_id["tid_a"].genres
    assert by_id["tid_b"].audio_features == {"energy": 0.3, "valence": 0.4, "tempo": 90.0}
    assert by_id["tid_b"].genres == ["jazz"]

    assert strategy["used_recommendations"] is False
    assert strategy["audio_features_filled"] == 2
    assert strategy["artist_genres_filled"] == 2


def test_recommendations_used_when_seed_genres_present(monkeypatch) -> None:
    client = _setup(monkeypatch)

    seen: dict[str, Any] = {"recs_called": False, "search_called": False}

    async def fake_get_seeds() -> list[str]:
        return ["chill", "study"]

    async def fake_recommendations(**kwargs) -> list[TrackCandidate]:
        seen["recs_called"] = True
        seen["recs_kwargs"] = kwargs
        return [
            TrackCandidate(
                title=f"R{i}",
                artist=f"Artist{i}",
                track_id=f"r{i}",
                artist_ids=[f"a{i}"],
                popularity=70 - i,
            )
            for i in range(40)
        ]

    async def fake_search(profile, target_count):
        seen["search_called"] = True
        return [], {"variants": [], "broadening_applied": False}

    async def fake_audio(track_ids):
        return {tid: {"energy": 0.5, "valence": 0.5, "tempo": 100.0} for tid in track_ids}

    async def fake_artists(artist_ids):
        return {aid: {"name": f"Name {aid}", "genres": ["chill"]} for aid in artist_ids}

    monkeypatch.setattr(client, "get_available_genre_seeds", fake_get_seeds, raising=False)
    monkeypatch.setattr(client, "get_recommendations", fake_recommendations, raising=False)
    monkeypatch.setattr(client, "search_tracks", fake_search, raising=False)
    monkeypatch.setattr(client, "get_audio_features", fake_audio, raising=False)
    monkeypatch.setattr(client, "get_artists", fake_artists, raising=False)

    profile = IntentProfile(
        mood="calm",
        activity="studying",
        seed_genres=["chill", "study"],
        target_audio={"energy": 0.3, "valence": 0.5},
        language="en",
    )

    candidates, strategy = asyncio.run(client.gather_candidates(profile, target_count=10))

    assert seen["recs_called"] is True
    assert strategy["used_recommendations"] is True
    assert len(candidates) >= 10
    # All enriched.
    assert all(c.audio_features is not None for c in candidates)
    # Recommendations supplied a sufficiently large pool, so search_tracks may
    # not be invoked. Either way, recs path was used.
    assert "chill" in strategy["recommendations_strategy"]["seed_genres"]
