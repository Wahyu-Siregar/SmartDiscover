"""/refine endpoint excludes previous track_ids and re-runs the pipeline."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models import RecommendationItem, RecommendResponse, TrackCandidate


client = TestClient(app)


def test_refine_excludes_previous_tracks(monkeypatch) -> None:
    captured: dict = {}

    async def fake_run_for_profile(self, *, text, target_count, previous_track_ids=None, refined_from=None):
        captured["text"] = text
        captured["previous_track_ids"] = set(previous_track_ids or [])
        captured["refined_from"] = refined_from
        return RecommendResponse(
            summary={"target_count": target_count or 5, "returned_count": 1, "intent_text": text},
            intent_profile={
                "mood": "calm",
                "activity": "listening",
                "genre": [],
                "energy": "low",
                "language": "en",
                "locale": "",
                "strict_locale": False,
            },
            query_strategy={"used_recommendations": False},
            recommendations=[
                RecommendationItem(
                    rank=1, title="Refined Track", artist="X",
                    spotify_url="", preview_url="", why="ok", score=0.9,
                )
            ],
            quality_notes={"refined_from": refined_from or ""},
        )

    monkeypatch.setattr(
        "app.services.pipeline.RecommendationPipeline._run_for_profile",
        fake_run_for_profile,
    )

    body = {
        "previous_profile": {
            "mood": "calm",
            "activity": "listening",
            "genre": ["indie"],
            "energy": "low",
            "language": "en",
            "locale": "",
            "strict_locale": False,
        },
        "previous_track_ids": ["tid1", "tid2", "tid3"],
        "refinement_text": "lebih upbeat",
        "target_count": 5,
    }

    resp = client.post("/refine", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendations"][0]["title"] == "Refined Track"

    # Pipeline was invoked with merged text and the previous ids forwarded.
    assert "lebih upbeat" in captured["text"]
    assert captured["previous_track_ids"] == {"tid1", "tid2", "tid3"}
    assert captured["refined_from"]  # short signature populated


def test_refine_validates_input() -> None:
    resp = client.post("/refine", json={"previous_profile": {}, "refinement_text": "ab"})
    assert resp.status_code == 422
