from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _fake_recommend_response(target_count: int = 5) -> dict:
    recommendations = [
        {
            "rank": i,
            "title": f"Track {i}",
            "artist": "Artist",
            "spotify_url": "https://open.spotify.com/track/test",
            "preview_url": "",
            "why": "Reason",
            "score": 0.9,
        }
        for i in range(1, target_count + 1)
    ]
    return {
        "summary": {
            "target_count": target_count,
            "returned_count": len(recommendations),
        },
        "intent_profile": {
            "mood": "neutral",
            "activity": "listening",
            "genre": [],
            "energy": "medium",
            "language": "id",
            "locale": "",
            "strict_locale": False,
        },
        "query_strategy": {"queries": ["test"]},
        "recommendations": recommendations,
        "quality_notes": {
            "llm_profiler_used": False,
            "llm_ranker_used": False,
            "fallback_used": False,
            "fallback_reason": "",
        },
    }


def test_recommend_default_schema_and_count(monkeypatch) -> None:
    async def fake_run(_payload):
        return _fake_recommend_response(15)

    monkeypatch.setattr("app.main.pipeline.run", fake_run)

    response = client.post(
        "/recommend",
        json={"text": "aku mau lagu buat belajar malam yang tenang dan fokus"},
    )

    assert response.status_code == 200
    body = response.json()

    assert set(body.keys()) == {
        "summary",
        "intent_profile",
        "query_strategy",
        "recommendations",
        "quality_notes",
    }

    summary = body["summary"]
    recommendations = body["recommendations"]

    assert summary["target_count"] == 15
    assert summary["returned_count"] == len(recommendations)
    assert len(recommendations) == 15

    ranks = [item["rank"] for item in recommendations]
    assert ranks == sorted(ranks)
    assert ranks[0] == 1


def test_recommend_custom_target_count(monkeypatch) -> None:
    async def fake_run(_payload):
        return _fake_recommend_response(5)

    monkeypatch.setattr("app.main.pipeline.run", fake_run)

    response = client.post(
        "/recommend",
        json={"text": "energetic running mix", "target_count": 5},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["summary"]["target_count"] == 5
    assert body["summary"]["returned_count"] == len(body["recommendations"])
    assert len(body["recommendations"]) == 5


def test_spotify_health_endpoint() -> None:
    response = client.get("/spotify/health")
    assert response.status_code == 200
    body = response.json()

    assert body["service"] == "spotify"
    assert "status" in body
    assert "ok" in body
    assert "details" in body
