"""Ranker min-output guard: when LLM returns < top_k, fill from heuristic."""
from __future__ import annotations

import asyncio

from app.models import IntentProfile, TrackCandidate
from app.services.openrouter_client import OpenRouterClient
from app.services.ranker import RankerAgent


def test_llm_partial_output_filled_with_heuristic(monkeypatch) -> None:
    llm = OpenRouterClient()
    llm.api_key = "test-key"

    # LLM only ranks the first 2 of 5 candidates; ranker must fill remaining.
    async def fake_chat_json(*args, **kwargs):
        return {
            "ranked": [
                {"idx": 1, "score": 0.95, "why": "LLM pick 1"},
                {"idx": 2, "score": 0.90, "why": "LLM pick 2"},
            ]
        }

    monkeypatch.setattr(llm, "chat_json", fake_chat_json, raising=False)

    ranker = RankerAgent(llm, max_per_artist=10)
    candidates = [
        TrackCandidate(
            title=f"T{i}", artist=f"A{i}", track_id=f"id{i}", artist_ids=[f"aid{i}"], popularity=80 - i
        )
        for i in range(1, 6)
    ]

    profile = IntentProfile(mood="neutral", activity="listening", language="en")
    ranked = asyncio.run(ranker.rank(profile, candidates, top_k=4))

    assert len(ranked) == 4
    track_ids = [c.track_id for c in ranked]
    # Both LLM picks must be present.
    assert "id1" in track_ids
    assert "id2" in track_ids
    # Filler tracks must come from the candidate pool.
    assert all(tid in {f"id{i}" for i in range(1, 6)} for tid in track_ids)
