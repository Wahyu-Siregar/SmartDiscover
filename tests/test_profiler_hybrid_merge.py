"""Profiler hybrid merge: heuristic Indonesian-locale genres survive even when LLM misses."""
from __future__ import annotations

import asyncio

from app.models import IntentProfile
from app.services.openrouter_client import OpenRouterClient
from app.services.profiler import ProfilerAgent


def _make_profiler(monkeypatch, llm_response: dict | None) -> ProfilerAgent:
    llm = OpenRouterClient()
    llm.api_key = "test-key"  # makes `enabled` property True

    async def fake_chat_json(*args, **kwargs):
        return llm_response

    monkeypatch.setattr(llm, "chat_json", fake_chat_json, raising=False)
    return ProfilerAgent(llm)


def test_heuristic_genre_survives_when_llm_misses(monkeypatch) -> None:
    # LLM returns empty genre but heuristic detects "batak".
    llm_payload = {
        "mood": "neutral",
        "activity": "listening",
        "genre": [],
        "energy": "medium",
        "language": "id",
        "locale": "",
        "strict_locale": False,
        "confidence": 0.8,
        "target_audio": {"energy": 0.5},
        "seed_genres": [],
    }
    agent = _make_profiler(monkeypatch, llm_payload)

    profile: IntentProfile = asyncio.run(agent.profile("lagu batak buat malam minggu"))
    assert "batak" in profile.genre, profile.genre
    assert profile.confidence > 0.0


def test_llm_unavailable_falls_back_cleanly(monkeypatch) -> None:
    # api_key empty -> enabled is False -> heuristic only path.
    llm = OpenRouterClient()
    llm.api_key = ""
    agent = ProfilerAgent(llm)
    profile = asyncio.run(agent.profile("lagu jawa campursari klasik"))
    assert "jawa" in profile.genre
    assert agent.last_used_llm is False


def test_target_audio_filled_from_heuristic_when_llm_misses_keys(monkeypatch) -> None:
    # LLM returns target_audio with only energy; mood-derived defaults should backfill.
    llm_payload = {
        "mood": "calm",
        "activity": "listening",
        "genre": [],
        "energy": "low",
        "language": "en",
        "locale": "",
        "strict_locale": False,
        "confidence": 0.7,
        "target_audio": {"energy": 0.25},
        "seed_genres": ["chill"],
    }
    agent = _make_profiler(monkeypatch, llm_payload)
    profile = asyncio.run(agent.profile("calm playlist for late-night reading"))
    assert profile.target_audio.get("energy") == 0.25  # LLM wins
    assert "tempo" in profile.target_audio  # heuristic fills missing
    assert profile.seed_genres  # union with heuristic mapping
