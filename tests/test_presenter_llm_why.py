"""Presenter generates `why` via LLM batch call when ranker omits them."""
from __future__ import annotations

import asyncio

from app.models import IntentProfile, TrackCandidate
from app.services.openrouter_client import OpenRouterClient
from app.services.presenter import PresenterAgent


def test_presenter_fills_missing_why_with_llm(monkeypatch) -> None:
    llm = OpenRouterClient()
    llm.api_key = "test-key"

    calls = {"count": 0}

    async def fake_chat_json(system_prompt, user_prompt, **kwargs):
        calls["count"] += 1
        return {
            "reasons": [
                {"idx": 1, "why": "Calm tempo fits late-night reading."},
                {"idx": 2, "why": "Mellow valence pairs with the mood."},
            ]
        }

    monkeypatch.setattr(llm, "chat_json", fake_chat_json, raising=False)

    presenter = PresenterAgent(llm)
    profile = IntentProfile(mood="calm", activity="listening", language="en")
    tracks = [
        TrackCandidate(title="A", artist="X", track_id="t1", score=0.9),
        TrackCandidate(title="B", artist="Y", track_id="t2", score=0.85),
    ]

    items = asyncio.run(presenter.present(profile, tracks))

    assert calls["count"] == 1
    assert items[0].why.startswith("Calm tempo")
    assert items[1].why.startswith("Mellow valence")
    assert presenter.last_used_llm is True


def test_presenter_skips_llm_when_all_tracks_already_have_why(monkeypatch) -> None:
    llm = OpenRouterClient()
    llm.api_key = "test-key"

    async def boom(*args, **kwargs):
        raise AssertionError("LLM should not be called when all reasons present")

    monkeypatch.setattr(llm, "chat_json", boom, raising=False)

    presenter = PresenterAgent(llm)
    profile = IntentProfile(language="en")
    tracks = [
        TrackCandidate(title="A", artist="X", why="ranker reason 1", score=0.9),
        TrackCandidate(title="B", artist="Y", why="ranker reason 2", score=0.8),
    ]
    items = asyncio.run(presenter.present(profile, tracks))
    assert items[0].why == "ranker reason 1"
    assert items[1].why == "ranker reason 2"
    assert presenter.last_used_llm is False


def test_presenter_preserves_audio_features_for_frontend() -> None:
    presenter = PresenterAgent()
    profile = IntentProfile(language="en")
    tracks = [
        TrackCandidate(
            title="A",
            artist="X",
            score=0.9,
            audio_features={"energy": 0.8, "valence": 0.6, "tempo": 120.0},
        ),
    ]

    items = asyncio.run(presenter.present(profile, tracks))

    assert items[0].audio_features == {"energy": 0.8, "valence": 0.6, "tempo": 120.0}
