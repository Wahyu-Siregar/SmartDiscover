"""Ranker enforces artist diversity (max 2 per artist when possible)."""
from __future__ import annotations

import asyncio

from app.models import IntentProfile, TrackCandidate
from app.services.openrouter_client import OpenRouterClient
from app.services.ranker import RankerAgent


def _candidate(tid: str, artist: str, artist_id: str, popularity: int = 60) -> TrackCandidate:
    return TrackCandidate(
        title=f"Track {tid}",
        artist=artist,
        track_id=tid,
        artist_ids=[artist_id],
        popularity=popularity,
        spotify_url="",
        preview_url="",
    )


def test_max_two_tracks_per_artist_when_possible() -> None:
    llm = OpenRouterClient()
    ranker = RankerAgent(llm, max_per_artist=2)

    # 5 from artist A, 5 from artist B; top_k=6 -> we expect 2A + 2B (then overflow to fill).
    candidates = [
        *[_candidate(f"A{i}", "Artist A", "aaa", 80 - i) for i in range(5)],
        *[_candidate(f"B{i}", "Artist B", "bbb", 75 - i) for i in range(5)],
    ]

    profile = IntentProfile(mood="neutral", activity="listening", language="en")
    ranked = asyncio.run(ranker.rank(profile, candidates, top_k=6))

    # First 4 picks must respect the cap.
    primary = ranked[:4]
    counts: dict[str, int] = {}
    for c in primary:
        counts[c.artist] = counts.get(c.artist, 0) + 1
    assert counts.get("Artist A", 0) <= 2
    assert counts.get("Artist B", 0) <= 2


def test_diversity_relaxed_when_pool_is_homogeneous() -> None:
    llm = OpenRouterClient()
    ranker = RankerAgent(llm, max_per_artist=2)

    # Only one artist available.
    candidates = [_candidate(f"A{i}", "Artist A", "aaa", 80 - i) for i in range(5)]
    profile = IntentProfile(mood="neutral", activity="listening", language="en")
    ranked = asyncio.run(ranker.rank(profile, candidates, top_k=4))

    # When there's no alternative, we must still return top_k results.
    assert len(ranked) == 4


def test_lyric_signals_boost_matching_tracks() -> None:
    llm = OpenRouterClient()
    ranker = RankerAgent(llm)
    matching = TrackCandidate(
        title="Quiet Rindu",
        artist="A",
        popularity=20,
        lyric_signals={
            "themes": ["longing", "heartbreak"],
            "sentiment": "sad",
            "match_score": 0.95,
        },
    )
    generic = TrackCandidate(title="Generic Hit", artist="B", popularity=80)

    ranked = asyncio.run(
        ranker.rank(
            IntentProfile(mood="sad", energy="low", language="en"),
            [generic, matching],
            top_k=2,
        )
    )

    assert ranked[0].title == "Quiet Rindu"


def test_lyric_preselection_uses_heuristic_fit_not_input_order() -> None:
    llm = OpenRouterClient()
    llm.api_key = ""
    ranker = RankerAgent(llm)
    generic = TrackCandidate(
        title="Generic Hit",
        artist="Popular",
        popularity=100,
    )
    matching = TrackCandidate(
        title="Sad Quiet Song",
        artist="Relevant",
        popularity=10,
    )

    selected = ranker.preselect_for_lyrics(
        IntentProfile(mood="sad", energy="low", language="en"), [generic, matching], limit=1
    )

    assert selected == [matching]


def test_lyric_signal_bonus_respects_evidence_confidence() -> None:
    bonus = RankerAgent._lyric_signal_bonus(
        IntentProfile(),
        {
            "match_score": 0.8,
            "confidence": 0.25,
        },
    )

    assert bonus == 0.2
