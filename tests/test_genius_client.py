from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.models import IntentProfile, TrackCandidate
from app.services.genius_client import GeniusClient


class _FakeSemanticMatcher:
    MODEL_ID = "intfloat/multilingual-e5-small"

    def __init__(self, scores_by_intent: dict[str, list[float]]) -> None:
        self.scores_by_intent = scores_by_intent
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, intent: str, passages: list[str]) -> list[float]:
        self.calls.append((intent, passages))
        return self.scores_by_intent[intent]


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


def test_meaning_request_batches_descriptions_into_relative_semantic_scores(monkeypatch) -> None:
    monkeypatch.setattr("app.services.genius_client.settings.genius_lyrics_enabled", True)
    monkeypatch.setattr("app.services.genius_client.settings.genius_access_token", "token")
    intent = "lagu tentang memaafkan diri setelah gagal"
    matcher = _FakeSemanticMatcher({intent: [0.91, 0.73]})
    client = GeniusClient(semantic_matcher=matcher)
    candidates = [
        TrackCandidate(title="Pulih", artist="A", track_id="1"),
        TrackCandidate(title="Pantai", artist="B", track_id="2"),
    ]
    metadata: dict[str, dict[str, Any]] = {
        "1": {
            "result": {"url": "https://genius.com/pulih"},
            "song": {"description_preview": "Berdamai dengan diri setelah mengalami kegagalan."},
        },
        "2": {
            "result": {"url": "https://genius.com/pantai"},
            "song": {"description_preview": "Perjalanan menikmati matahari di tepi pantai."},
        },
    }

    async def fake_lookup(track: TrackCandidate):
        return metadata[track.track_id]

    monkeypatch.setattr(client, "lookup_track", fake_lookup)
    asyncio.run(
        client.enrich_candidates(
            IntentProfile(language="id", lyrical_intent=intent, meaning_required=True),
            candidates,
        )
    )

    assert matcher.calls == [
        (
            intent,
            [
                "Berdamai dengan diri setelah mengalami kegagalan.",
                "Perjalanan menikmati matahari di tepi pantai.",
            ],
        )
    ]
    assert candidates[0].lyric_signals["semantic_score"] == 0.91
    assert candidates[1].lyric_signals["semantic_score"] == 0.73
    assert candidates[0].lyric_signals["match_score"] == 1.0
    assert candidates[1].lyric_signals["match_score"] == 0.0
    assert candidates[0].lyric_signals["semantic_model"] == matcher.MODEL_ID


def test_relative_semantic_scores_are_neutral_without_ordering_signal() -> None:
    assert GeniusClient._relative_scores([0.8]) == [0.5]
    assert GeniusClient._relative_scores([0.8, 0.8]) == [0.5, 0.5]


def test_non_meaning_request_does_not_call_semantic_matcher(monkeypatch) -> None:
    monkeypatch.setattr("app.services.genius_client.settings.genius_lyrics_enabled", True)
    monkeypatch.setattr("app.services.genius_client.settings.genius_access_token", "token")
    matcher = _FakeSemanticMatcher({})
    client = GeniusClient(semantic_matcher=matcher)
    track = TrackCandidate(title="Tenang", artist="A", track_id="1")

    async def fake_lookup(_track: TrackCandidate):
        return {
            "result": {"url": "https://genius.com/tenang"},
            "song": {"description_preview": "Musik tenang untuk malam."},
        }

    monkeypatch.setattr(client, "lookup_track", fake_lookup)
    asyncio.run(client.enrich_candidates(IntentProfile(mood="calm", language="id"), [track]))

    assert matcher.calls == []
    assert "semantic_score" not in track.lyric_signals


def test_cached_metadata_is_rescored_for_each_intent(monkeypatch) -> None:
    monkeypatch.setattr("app.services.genius_client.settings.genius_lyrics_enabled", True)
    monkeypatch.setattr("app.services.genius_client.settings.genius_access_token", "token")
    first_intent = "berdamai dengan kegagalan"
    second_intent = "menikmati pantai"
    matcher = _FakeSemanticMatcher(
        {
            first_intent: [0.9, 0.7],
            second_intent: [0.6, 0.95],
        }
    )
    client = GeniusClient(semantic_matcher=matcher)
    candidates = [
        TrackCandidate(title="Pulih", artist="A", track_id="1"),
        TrackCandidate(title="Pantai", artist="B", track_id="2"),
    ]
    client._cache.set(
        "spotify::1",
        {"result": {}, "song": {"description_preview": "Berdamai setelah gagal."}},
    )
    client._cache.set(
        "spotify::2",
        {"result": {}, "song": {"description_preview": "Berlibur di pantai."}},
    )

    asyncio.run(
        client.enrich_candidates(
            IntentProfile(language="id", lyrical_intent=first_intent, meaning_required=True),
            candidates,
        )
    )
    first_scores = [candidate.lyric_signals["match_score"] for candidate in candidates]

    asyncio.run(
        client.enrich_candidates(
            IntentProfile(language="id", lyrical_intent=second_intent, meaning_required=True),
            candidates,
        )
    )
    second_scores = [candidate.lyric_signals["match_score"] for candidate in candidates]

    assert first_scores == [1.0, 0.0]
    assert second_scores == [0.0, 1.0]
    assert [intent for intent, _ in matcher.calls] == [first_intent, second_intent]
