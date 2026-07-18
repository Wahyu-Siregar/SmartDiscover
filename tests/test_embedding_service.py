from __future__ import annotations

import pytest

from app.services.embedding_service import E5SemanticMatcher


class _RecordingEncoder:
    def __init__(self, rows: list[list[float]]) -> None:
        self.rows = rows
        self.calls: list[tuple[list[str], dict]] = []

    def encode(self, texts: list[str], **kwargs):
        self.calls.append((texts, kwargs))
        return self.rows


def test_e5_scores_prefixed_normalized_query_and_passages() -> None:
    encoder = _RecordingEncoder([[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]])
    matcher = E5SemanticMatcher(encoder=encoder)

    scores = matcher.score(
        "memaafkan diri setelah gagal",
        ["tentang berdamai dengan kegagalan", "tentang liburan di pantai"],
    )

    assert scores == [0.8, 0.0]
    assert encoder.calls == [
        (
            [
                "query: memaafkan diri setelah gagal",
                "passage: tentang berdamai dengan kegagalan",
                "passage: tentang liburan di pantai",
            ],
            {
                "normalize_embeddings": True,
                "convert_to_numpy": True,
                "show_progress_bar": False,
            },
        )
    ]


def test_e5_requires_load_before_scoring() -> None:
    with pytest.raises(RuntimeError, match=r"load\(\).+before score"):
        E5SemanticMatcher().score("intent", ["description"])


def test_e5_empty_passages_skip_encoder() -> None:
    encoder = _RecordingEncoder([])

    assert E5SemanticMatcher(encoder=encoder).score("intent", []) == []
    assert encoder.calls == []


def test_e5_rejects_malformed_embedding_count() -> None:
    matcher = E5SemanticMatcher(encoder=_RecordingEncoder([[1.0, 0.0]]))

    with pytest.raises(RuntimeError, match="unexpected embedding count"):
        matcher.score("intent", ["description"])
