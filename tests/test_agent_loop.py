"""Agent loop: tools execute, finalize is reached, iteration cap honored."""
from __future__ import annotations

import asyncio

from app.models import IntentProfile, TrackCandidate
from app.services.agent_loop import AgenticOrchestrator
from app.services.openrouter_client import OpenRouterClient
from app.services.spotify_client import SpotifyClient


def _make_orchestrator(monkeypatch, llm_responses: list[dict]) -> AgenticOrchestrator:
    monkeypatch.setattr("app.services.agent_loop.settings.agent_loop_enabled", True, raising=False)
    monkeypatch.setattr("app.services.agent_loop.settings.agent_loop_max_iterations", 3, raising=False)
    monkeypatch.setattr("app.services.agent_loop.settings.agent_loop_timeout_s", 10.0, raising=False)

    llm = OpenRouterClient()
    llm.api_key = "test-key"

    async def fake_chat_with_tools(system_prompt, user_prompt, tools, tool_executor, **kwargs):
        # Replay each canned response: drive the executor for tool_calls,
        # stop when the model produces a turn without tool_calls.
        trace: list = []
        iterations = 0
        for resp in llm_responses:
            iterations += 1
            tool_calls = resp.get("tool_calls") or []
            if not tool_calls:
                return {"message": resp, "trace": trace, "iterations": iterations}
            for call in tool_calls:
                fn = call.get("function", {})
                import json as _json
                args = _json.loads(fn.get("arguments", "{}"))
                result = await tool_executor(fn["name"], args)
                trace.append({"name": fn["name"], "arguments": args, "result_summary": str(result)[:80]})
        return {"message": llm_responses[-1], "trace": trace, "iterations": iterations}

    monkeypatch.setattr(llm, "chat_with_tools", fake_chat_with_tools, raising=False)

    spotify = SpotifyClient()

    async def fake_audio(ids):
        return {tid: {"energy": 0.5, "valence": 0.5, "tempo": 100.0} for tid in ids}

    monkeypatch.setattr(spotify, "get_audio_features", fake_audio, raising=False)

    return AgenticOrchestrator(llm, spotify)


def test_agent_loop_executes_finalize_and_returns_ordered_pool(monkeypatch) -> None:
    candidates = [
        TrackCandidate(title=f"T{i}", artist=f"A{i}", track_id=f"tid{i}", artist_ids=[f"a{i}"])
        for i in range(5)
    ]
    profile = IntentProfile(mood="calm", activity="listening", language="en")

    llm_responses = [
        {
            "tool_calls": [
                {
                    "id": "1",
                    "function": {
                        "name": "finalize",
                        "arguments": '{"track_ids": ["tid2", "tid0"], "reasoning": "best fit"}',
                    },
                }
            ]
        },
        {"content": "done", "tool_calls": []},
    ]

    orchestrator = _make_orchestrator(monkeypatch, llm_responses)
    result = asyncio.run(orchestrator.run(profile, candidates, target_count=3))
    assert result is not None
    refined, info = result

    # finalize order honored at the front of the list.
    assert refined[0].track_id == "tid2"
    assert refined[1].track_id == "tid0"
    assert "finalize" in info["tools_called"]


def test_agent_loop_disabled_returns_none(monkeypatch) -> None:
    monkeypatch.setattr("app.services.agent_loop.settings.agent_loop_enabled", False, raising=False)
    llm = OpenRouterClient()
    llm.api_key = "test-key"
    orchestrator = AgenticOrchestrator(llm, SpotifyClient())
    result = asyncio.run(
        orchestrator.run(
            IntentProfile(language="en"),
            [TrackCandidate(title="x", artist="y", track_id="z")],
            target_count=1,
        )
    )
    assert result is None
