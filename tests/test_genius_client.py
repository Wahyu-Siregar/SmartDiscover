from __future__ import annotations

import asyncio

import httpx

from app.models import IntentProfile, TrackCandidate
from app.services.genius_client import GeniusClient


class _FakeGeniusHttpClient:
    def __init__(self) -> None:
        self.urls: list[str] = []

    async def get(self, url, **kwargs):
        self.urls.append(url)
        if url.endswith("/search"):
            return httpx.Response(
                200,
                json={
                    "response": {
                        "hits": [
                            {
                                "result": {
                                    "id": 11,
                                    "title": "Rindu Berat",
                                    "full_title": "Rindu Berat by Sore",
                                    "url": "https://genius.com/sore-rindu-berat-lyrics",
                                    "primary_artist": {"name": "Sore"},
                                }
                            }
                        ]
                    }
                },
                request=httpx.Request("GET", url),
            )
        return httpx.Response(
            200,
            json={
                "response": {
                    "song": {
                        "lyrics_state": "complete",
                        "description_preview": "Lagu tentang rindu, kangen, dan patah hati.",
                    }
                }
            },
            request=httpx.Request("GET", url),
        )


def test_genius_enrich_candidates_adds_bounded_lyric_signals(monkeypatch) -> None:
    monkeypatch.setattr("app.services.genius_client.settings.genius_lyrics_enabled", True)
    monkeypatch.setattr("app.services.genius_client.settings.genius_access_token", "token")

    http_client = _FakeGeniusHttpClient()
    client = GeniusClient()
    client.attach_client(http_client)  # type: ignore[arg-type]
    candidates = [
        TrackCandidate(title="Rindu Berat", artist="Sore", track_id="1"),
        TrackCandidate(title="Tidak Diproses", artist="A", track_id="2"),
    ]

    info = asyncio.run(
        client.enrich_candidates(
            IntentProfile(mood="sad", energy="low", language="id"),
            candidates,
            limit=1,
        )
    )

    assert info["lookups"] == 1
    assert info["filled"] == 1
    assert candidates[0].lyric_signals is not None
    assert candidates[0].lyric_signals["source"] == "genius"
    assert candidates[0].lyric_signals["source_kind"] == "metadata_description"
    assert "longing" in candidates[0].lyric_signals["themes"]
    assert candidates[1].lyric_signals is None


def test_best_hit_rejects_unrelated_first_result() -> None:
    track = TrackCandidate(title="Rindu Berat", artist="Sore")
    hits = [
        {
            "result": {
                "title": "Completely Different",
                "primary_artist": {"name": "Another Artist"},
            }
        }
    ]

    assert GeniusClient._best_hit(track, hits) is None


def test_best_hit_rejects_missing_title() -> None:
    track = TrackCandidate(title="Rindu Berat", artist="Sore")
    hits = [
        {
            "result": {
                "title": "",
                "primary_artist": {"name": "Sore"},
            }
        }
    ]

    assert GeniusClient._best_hit(track, hits) is None


def test_theme_matching_uses_word_boundaries() -> None:
    assert GeniusClient._themes("dismissed by everyone") == []


def test_sentiment_ignores_directly_negated_positive_words() -> None:
    assert GeniusClient._sentiment("not happy, no love, never party") == "neutral"


def test_title_only_metadata_has_no_semantic_match_score() -> None:
    client = GeniusClient()
    track = TrackCandidate(title="Unknown Meaning", artist="A")

    signal = client._build_signal(
        IntentProfile(mood="sad", energy="low", language="en"),
        track,
        {
            "title": track.title,
            "full_title": "Unknown Meaning by A",
            "primary_artist": {"name": track.artist},
        },
        {},
    )

    assert signal["source_kind"] == "metadata_title_only"
    assert signal["confidence"] == 0.1
    assert signal["themes"] == []
    assert signal["sentiment"] == "unknown"
    assert signal["match_score"] == 0.0


def test_description_metadata_scores_lyrical_intent_overlap() -> None:
    client = GeniusClient()
    profile = IntentProfile(
        language="id",
        lyrical_intent="lagu tentang memaafkan diri setelah gagal",
        meaning_required=True,
    )
    track = TrackCandidate(title="Pulih", artist="A")
    result = {"title": track.title, "primary_artist": {"name": track.artist}}

    related = client._build_signal(
        profile,
        track,
        result,
        {"description_preview": "Lagu ini membahas memaafkan diri setelah gagal."},
    )
    unrelated = client._build_signal(
        profile,
        track,
        result,
        {"description_preview": "Lagu ini menggambarkan perjalanan menikmati pantai."},
    )

    assert related["match_score"] > unrelated["match_score"]
