from __future__ import annotations

import asyncio

from app.models import IntentProfile, RecommendRequest, TrackCandidate
from app.services.pipeline import RecommendationPipeline


def _seed_pipeline(monkeypatch) -> RecommendationPipeline:
    pipeline = RecommendationPipeline()

    async def fake_profile(text: str) -> IntentProfile:
        return IntentProfile(mood="calm", activity="studying", language="en")

    async def fake_candidates(profile: IntentProfile, target_count: int):
        return (
            [
                TrackCandidate(
                    title="A",
                    artist="Artist A",
                    track_id="a",
                    spotify_url="",
                    preview_url="",
                    popularity=80,
                    why="Fits the study mood.",
                ),
                TrackCandidate(
                    title="B",
                    artist="Artist B",
                    track_id="b",
                    spotify_url="",
                    preview_url="",
                    popularity=70,
                    why="Calm enough for focus.",
                ),
            ],
            {"variants": ["calm studying"], "used_recommendations": False},
        )

    monkeypatch.setattr(pipeline.profiler, "profile", fake_profile, raising=False)
    monkeypatch.setattr(pipeline.spotify, "gather_candidates", fake_candidates, raising=False)
    monkeypatch.setattr("app.services.pipeline.settings.agent_loop_enabled", True, raising=False)
    return pipeline


def test_agentic_mode_linear_bypasses_orchestrator(monkeypatch) -> None:
    pipeline = _seed_pipeline(monkeypatch)
    pipeline.llm.api_key = "test-key"
    calls = 0

    async def fake_orchestrator(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr(pipeline.orchestrator, "run", fake_orchestrator, raising=False)

    response = asyncio.run(
        pipeline.run(RecommendRequest(text="calm study music", target_count=2, agentic_mode="linear"))
    )

    assert calls == 0
    assert response.quality_notes["agentic"]["mode_requested"] == "linear"
    assert response.quality_notes["agentic"]["mode_effective"] == "linear"
    assert response.quality_notes["agentic"]["status"] == "bypassed"


def test_agentic_mode_agentic_runs_orchestrator_when_llm_enabled(monkeypatch) -> None:
    pipeline = _seed_pipeline(monkeypatch)
    pipeline.llm.api_key = "test-key"
    calls = 0

    async def fake_orchestrator(profile, candidates, top_k, **_kwargs):
        nonlocal calls
        calls += 1
        return candidates, {
            "iterations": 2,
            "tools_called": ["filter_by_audio", "finalize"],
            "trace": [{"name": "finalize", "result_summary": "accepted"}],
            "finalized": True,
            "status": "completed",
        }

    monkeypatch.setattr(pipeline.orchestrator, "run", fake_orchestrator, raising=False)

    response = asyncio.run(
        pipeline.run(RecommendRequest(text="calm study music", target_count=2, agentic_mode="agentic"))
    )

    assert calls == 1
    agentic = response.quality_notes["agentic"]
    assert agentic["mode_requested"] == "agentic"
    assert agentic["mode_effective"] == "agentic"
    assert agentic["status"] == "completed"
    assert agentic["iterations"] == 2
    assert agentic["tools_called"] == ["filter_by_audio", "finalize"]
    assert agentic["finalized"] is True


def test_agentic_mode_agentic_falls_back_when_llm_disabled(monkeypatch) -> None:
    pipeline = _seed_pipeline(monkeypatch)
    pipeline.llm.api_key = ""
    calls = 0

    async def fake_orchestrator(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr(pipeline.orchestrator, "run", fake_orchestrator, raising=False)

    response = asyncio.run(
        pipeline.run(RecommendRequest(text="calm study music", target_count=2, agentic_mode="agentic"))
    )

    assert calls == 0
    agentic = response.quality_notes["agentic"]
    assert agentic["mode_requested"] == "agentic"
    assert agentic["mode_effective"] == "linear"
    assert agentic["status"] == "unavailable_llm"
    assert agentic["fallback_reason"] == "LLM is disabled."
