"""Validate input cap and rate limiting on /recommend & /api/prompt-suggestions."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app, limiter


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_limiter():
    # slowapi keeps in-process state per route; reset between tests.
    limiter.reset()
    yield
    limiter.reset()


def test_recommend_rejects_oversize_text() -> None:
    resp = client.post("/recommend", json={"text": "x" * 501})
    assert resp.status_code == 422


def test_recommend_rejects_too_short_text() -> None:
    resp = client.post("/recommend", json={"text": "ab"})
    assert resp.status_code == 422


def test_recommend_rate_limit(monkeypatch) -> None:
    # Tighten the limit just for this test by re-decorating is invasive; instead
    # we drive through the configured 10/minute and expect a 429 on the 11th.
    async def fake_run(_payload):
        from app.models import RecommendResponse

        return RecommendResponse(
            summary={"target_count": 1, "returned_count": 0},
            intent_profile={"mood": "neutral", "activity": "listening", "genre": [], "energy": "medium", "language": "id"},
            query_strategy={},
            recommendations=[],
            quality_notes={},
        )

    monkeypatch.setattr("app.main.pipeline.run", fake_run)

    body = {"text": "lagu santai malam", "target_count": 1}

    statuses = []
    for _ in range(12):
        statuses.append(client.post("/recommend", json=body).status_code)

    assert 429 in statuses, f"expected at least one 429, got: {statuses}"
    assert statuses.count(200) <= 10
