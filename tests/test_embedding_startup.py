from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import lifespan
from app.services.pipeline import RecommendationPipeline


class _FakeSemanticMatcher:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.loads = 0

    def load(self) -> None:
        self.loads += 1
        if self.error:
            raise self.error


class _PromptStoreStub:
    def attach_client(self, _client) -> None:
        pass


def _lifespan_app(matcher: _FakeSemanticMatcher) -> FastAPI:
    test_app = FastAPI(lifespan=lifespan)
    test_app.state.pipeline = RecommendationPipeline(semantic=matcher)
    test_app.state.prompt_store = _PromptStoreStub()
    return test_app


def test_lifespan_loads_e5_before_startup_completes() -> None:
    matcher = _FakeSemanticMatcher()

    with TestClient(_lifespan_app(matcher)):
        assert matcher.loads == 1


def test_lifespan_propagates_e5_load_failure() -> None:
    matcher = _FakeSemanticMatcher(RuntimeError("model unavailable"))

    with pytest.raises(RuntimeError, match="model unavailable"):
        with TestClient(_lifespan_app(matcher)):
            pass
