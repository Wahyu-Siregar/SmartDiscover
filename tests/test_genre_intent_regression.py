import pytest

from fastapi.testclient import TestClient

from app.main import app, pipeline
from app.models import TrackCandidate


client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_external_services(monkeypatch):
    async def fake_enrich_candidates(*args, **kwargs):
        return {"enabled": False, "lookups": 0, "filled": 0, "source": "genius"}

    monkeypatch.setattr(pipeline.llm, "api_key", "")
    monkeypatch.setattr(pipeline.genius, "enrich_candidates", fake_enrich_candidates)


def test_genre_only_prompt_prioritizes_matching_tracks(monkeypatch) -> None:
    async def fake_search_tracks(profile, target_count):
        assert "batak" in [g.lower() for g in profile.genre]
        candidates = [
            TrackCandidate(
                title="Ahu Do Ho",
                artist="Batak Voice",
                spotify_url="https://open.spotify.com/track/batak1",
                preview_url="",
                popularity=60,
            ),
            TrackCandidate(
                title="Simalungun Night",
                artist="North Sumatra Ensemble",
                spotify_url="https://open.spotify.com/track/batak2",
                preview_url="",
                popularity=58,
            ),
            TrackCandidate(
                title="Generic Pop Love",
                artist="Random Artist",
                spotify_url="https://open.spotify.com/track/pop1",
                preview_url="",
                popularity=95,
            ),
        ]
        return candidates, {"variants": ["lagu batak"], "broadening_applied": False}

    monkeypatch.setattr(pipeline.spotify, "gather_candidates", fake_search_tracks)

    response = client.post("/recommend", json={"text": "lagu batak", "target_count": 3})

    assert response.status_code == 200
    body = response.json()
    recommendations = body["recommendations"]

    assert len(recommendations) == 3
    top_two_text = " ".join(
        f"{recommendations[i]['title']} {recommendations[i]['artist']}".lower()
        for i in range(2)
    )
    assert any(keyword in top_two_text for keyword in ["batak", "simalungun"])


def test_genre_only_prompt_jawa_prioritizes_matching_tracks(monkeypatch) -> None:
    async def fake_search_tracks(profile, target_count):
        detected = {g.lower() for g in profile.genre}
        assert detected.intersection({"jawa", "javanese"})
        candidates = [
            TrackCandidate(
                title="Campursari Tresno",
                artist="Jawa Harmoni",
                spotify_url="https://open.spotify.com/track/jawa1",
                preview_url="",
                popularity=58,
            ),
            TrackCandidate(
                title="Keroncong Senja",
                artist="Javanese Ensemble",
                spotify_url="https://open.spotify.com/track/jawa2",
                preview_url="",
                popularity=57,
            ),
            TrackCandidate(
                title="Mainstream Dance",
                artist="Top Chart Artist",
                spotify_url="https://open.spotify.com/track/pop2",
                preview_url="",
                popularity=96,
            ),
        ]
        return candidates, {"variants": ["lagu jawa"], "broadening_applied": False}

    monkeypatch.setattr(pipeline.spotify, "gather_candidates", fake_search_tracks)

    response = client.post("/recommend", json={"text": "lagu jawa", "target_count": 3})

    assert response.status_code == 200
    body = response.json()
    recommendations = body["recommendations"]

    assert len(recommendations) == 3
    top_two_text = " ".join(
        f"{recommendations[i]['title']} {recommendations[i]['artist']}".lower()
        for i in range(2)
    )
    assert any(keyword in top_two_text for keyword in ["jawa", "javanese", "campursari", "keroncong"])


def test_genre_only_prompt_minang_prioritizes_matching_tracks(monkeypatch) -> None:
    async def fake_search_tracks(profile, target_count):
        detected = {g.lower() for g in profile.genre}
        assert detected.intersection({"minang", "minangkabau"})
        candidates = [
            TrackCandidate(
                title="Rang Minang Rindu",
                artist="Minangkabau Voice",
                spotify_url="https://open.spotify.com/track/minang1",
                preview_url="",
                popularity=59,
            ),
            TrackCandidate(
                title="Padang Evening",
                artist="Ranah Minang Group",
                spotify_url="https://open.spotify.com/track/minang2",
                preview_url="",
                popularity=56,
            ),
            TrackCandidate(
                title="Global Hit Anthem",
                artist="Top Chart Artist",
                spotify_url="https://open.spotify.com/track/pop3",
                preview_url="",
                popularity=98,
            ),
        ]
        return candidates, {"variants": ["lagu minang"], "broadening_applied": False}

    monkeypatch.setattr(pipeline.spotify, "gather_candidates", fake_search_tracks)

    response = client.post("/recommend", json={"text": "lagu minang", "target_count": 3})

    assert response.status_code == 200
    body = response.json()
    recommendations = body["recommendations"]

    assert len(recommendations) == 3
    top_two_text = " ".join(
        f"{recommendations[i]['title']} {recommendations[i]['artist']}".lower()
        for i in range(2)
    )
    assert any(keyword in top_two_text for keyword in ["minang", "minangkabau", "padang"])
