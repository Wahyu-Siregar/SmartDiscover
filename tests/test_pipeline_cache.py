"""Pipeline-level cache: identical prompts must not re-call profiler/spotify."""
from __future__ import annotations

import asyncio

from app.models import IntentProfile, RecommendRequest, TrackCandidate
from app.services.pipeline import RecommendationPipeline


def test_pipeline_caches_profile_and_search(monkeypatch) -> None:
    pipeline = RecommendationPipeline()

    profile_calls = 0
    search_calls = 0

    async def fake_profile(text: str) -> IntentProfile:
        nonlocal profile_calls
        profile_calls += 1
        return IntentProfile(mood="calm", activity="studying", genre=["lo-fi"], energy="low", language="id")

    async def fake_gather(profile, target_count):
        nonlocal search_calls
        search_calls += 1
        return (
            [
                TrackCandidate(title="A", artist="X", spotify_url="", preview_url="", popularity=80),
                TrackCandidate(title="B", artist="Y", spotify_url="", preview_url="", popularity=70),
            ],
            {"variants": ["q"], "broadening_applied": False},
        )

    pipeline.profiler.profile = fake_profile  # type: ignore[assignment]
    pipeline.spotify.gather_candidates = fake_gather  # type: ignore[assignment]

    payload = RecommendRequest(text="lagu fokus malam", target_count=2)

    async def _run_twice() -> None:
        await pipeline.run(payload)
        await pipeline.run(payload)

    asyncio.run(_run_twice())

    assert profile_calls == 1, "profile must be cached for identical prompt"
    assert search_calls == 1, "search must be cached for identical profile signature"


def test_pipeline_cache_keys_differ_for_different_prompts(monkeypatch) -> None:
    pipeline = RecommendationPipeline()
    profile_calls = 0

    async def fake_profile(text: str) -> IntentProfile:
        nonlocal profile_calls
        profile_calls += 1
        # Different text -> different profile signature.
        return IntentProfile(mood=text[:5], activity="listening", language="id")

    async def fake_gather(profile, target_count):
        return ([], {"variants": [], "broadening_applied": False})

    pipeline.profiler.profile = fake_profile  # type: ignore[assignment]
    pipeline.spotify.gather_candidates = fake_gather  # type: ignore[assignment]

    async def _run() -> None:
        await pipeline.run(RecommendRequest(text="prompt-one"))
        await pipeline.run(RecommendRequest(text="prompt-two"))

    asyncio.run(_run())
    assert profile_calls == 2
