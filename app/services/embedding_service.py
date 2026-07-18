from __future__ import annotations

from typing import Any


class E5SemanticMatcher:
    MODEL_ID = "intfloat/multilingual-e5-small"

    def __init__(self, encoder: Any | None = None) -> None:
        self._encoder = encoder

    def load(self) -> None:
        if self._encoder is not None:
            return
        from sentence_transformers import SentenceTransformer

        self._encoder = SentenceTransformer(self.MODEL_ID)

    def score(self, intent: str, passages: list[str]) -> list[float]:
        if self._encoder is None:
            raise RuntimeError("E5SemanticMatcher.load() must be called before score()")
        if not passages:
            return []

        texts = [f"query: {intent}", *[f"passage: {passage}" for passage in passages]]
        embeddings = self._encoder.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if len(embeddings) != len(texts):
            raise RuntimeError("E5 encoder returned an unexpected embedding count")

        query = embeddings[0]
        scores: list[float] = []
        for passage in embeddings[1:]:
            if len(query) != len(passage):
                raise RuntimeError("E5 encoder returned inconsistent embedding dimensions")
            scores.append(round(sum(float(a) * float(b) for a, b in zip(query, passage)), 6))
        return scores
