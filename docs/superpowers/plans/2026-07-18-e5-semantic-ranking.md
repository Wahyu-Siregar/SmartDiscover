# E5 Semantic Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `intfloat/multilingual-e5-small` a fail-fast startup dependency and use it to rank Genius descriptions against lyric-sensitive user intent.

**Architecture:** Add one small `E5SemanticMatcher`, owned by `RecommendationPipeline` and loaded by FastAPI lifespan. `GeniusClient` caches only profile-independent metadata, scores all current descriptions in one background-thread batch, and writes relative semantic scores into the existing lyric signal consumed by the ranker.

**Tech Stack:** Python 3.12, FastAPI lifespan, `sentence-transformers==5.6.0`, `intfloat/multilingual-e5-small`, pytest.

## Global Constraints

- The fixed model ID is exactly `intfloat/multilingual-e5-small`.
- Model loading is mandatory during FastAPI startup; load failure aborts startup.
- Inputs use `query: ` and `passage: ` prefixes with normalized embeddings.
- Semantic inference runs only when `meaning_required=true` and `lyrical_intent` is non-empty.
- Genius remains metadata-only evidence; do not claim access to full lyrics.
- Do not add a vector database, fallback matcher, model selector, ONNX path, or GPU-specific configuration.
- All committed tests run without Spotify Premium and without downloading E5.
- Preserve the user's existing `.gitignore` modification and do not stage `graphify-out/`.

---

## File Structure

- Create `app/services/embedding_service.py`: load E5 and calculate query-to-passage cosine scores.
- Create `tests/test_embedding_service.py`: pure unit coverage with an injected recording encoder.
- Modify `app/services/genius_client.py`: cache raw Genius metadata and apply per-request semantic scoring.
- Modify `tests/test_genius_client.py`: semantic batching, relative scoring, cache regression, and non-semantic behavior.
- Modify `app/services/pipeline.py`: own and inject the shared matcher.
- Modify `app/main.py`: load E5 during lifespan before reporting ready.
- Create `tests/test_embedding_startup.py`: lifespan success and fail-fast tests using a local app and fake matcher.
- Modify `requirements.txt`: pin `sentence-transformers==5.6.0`.
- Modify `README.md`: document semantic enrichment, first-start model download, and metadata-only limitation.

---

### Task 1: E5 Semantic Matcher

**Files:**
- Create: `tests/test_embedding_service.py`
- Create: `app/services/embedding_service.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `E5SemanticMatcher.MODEL_ID: str`
- Produces: `E5SemanticMatcher.load() -> None`
- Produces: `E5SemanticMatcher.score(intent: str, passages: list[str]) -> list[float]`

- [ ] **Step 1: Write the failing matcher tests**

Create `tests/test_embedding_service.py`:

```python
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
```

- [ ] **Step 2: Run the matcher tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_embedding_service.py -q
```

Expected: collection fails because `app.services.embedding_service` does not exist.

- [ ] **Step 3: Implement the minimum matcher and dependency pin**

Create `app/services/embedding_service.py`:

```python
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
```

Append the runtime dependency to `requirements.txt` before the `# dev` marker:

```text
sentence-transformers==5.6.0
```

- [ ] **Step 4: Run the matcher tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_embedding_service.py -q
```

Expected: `4 passed` without importing or downloading Sentence Transformers because every scoring test injects an encoder.

- [ ] **Step 5: Commit the matcher**

```powershell
git add app/services/embedding_service.py tests/test_embedding_service.py requirements.txt
git commit -m "feat: add E5 semantic matcher"
```

---

### Task 2: Per-Request Genius Semantic Scoring

**Files:**
- Modify: `tests/test_genius_client.py`
- Modify: `app/services/genius_client.py`

**Interfaces:**
- Consumes: `E5SemanticMatcher.score(intent, passages) -> list[float]`
- Produces: `GeniusClient(semantic_matcher: E5SemanticMatcher | None = None)`
- Produces: `GeniusClient.lookup_track(track: TrackCandidate) -> dict[str, Any] | None`
- Produces: lyric signals with `semantic_score`, `semantic_model`, and relative `match_score` for meaning-required requests.

- [ ] **Step 1: Replace the lexical-overlap test with failing semantic batch tests**

In `tests/test_genius_client.py`, import `Any` and add this test double:

```python
from typing import Any


class _FakeSemanticMatcher:
    MODEL_ID = "intfloat/multilingual-e5-small"

    def __init__(self, scores_by_intent: dict[str, list[float]]) -> None:
        self.scores_by_intent = scores_by_intent
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, intent: str, passages: list[str]) -> list[float]:
        self.calls.append((intent, passages))
        return self.scores_by_intent[intent]
```

Replace `test_description_metadata_scores_lyrical_intent_overlap` with:

```python
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
```

Add neutral normalization and non-meaning tests:

```python
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
```

- [ ] **Step 2: Run semantic Genius tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_genius_client.py -q
```

Expected: failures show that `GeniusClient` does not accept `semantic_matcher`, does not batch E5 scoring, and lacks `_relative_scores`.

- [ ] **Step 3: Refactor Genius metadata caching and apply semantic scores**

In `app/services/genius_client.py`:

1. Import `E5SemanticMatcher`.
2. Remove `LYRICAL_INTENT_STOPWORDS` and `_lyrical_intent_overlap`.
3. Change construction and lookup to cache profile-independent metadata:

```python
class GeniusClient:
    BASE_URL = "https://api.genius.com"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        semantic_matcher: E5SemanticMatcher | None = None,
    ) -> None:
        self._client = client
        self._semantic_matcher = semantic_matcher or E5SemanticMatcher()
        self._cache: TTLCache[dict[str, Any] | None] = TTLCache(
            max_size=512,
            ttl_seconds=float(settings.genius_lyrics_cache_ttl_s),
        )

    async def lookup_track(self, track: TrackCandidate) -> dict[str, Any] | None:
        key = self._cache_key(track)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        query = f"{track.title} {track.artist}".strip()
        if not query:
            return None

        client = self._require_client()
        try:
            search_resp = await client.get(
                f"{self.BASE_URL}/search",
                params={"q": query},
                headers=self._headers(),
                timeout=12.0,
            )
            if search_resp.status_code != 200:
                return None
            hit = self._best_hit(track, search_resp.json().get("response", {}).get("hits", []) or [])
            if not hit:
                return None

            result = hit.get("result", {}) or {}
            metadata = {"result": result, "song": await self._fetch_song(result.get("id"))}
            self._cache.set(key, metadata)
            return metadata
        except Exception:
            return None
```

Replace the gather-and-attach portion of `enrich_candidates()` with:

```python
        selected = candidates[:safe_limit]
        metadata_rows = await asyncio.gather(
            *[self.lookup_track(track) for track in selected],
            return_exceptions=True,
        )

        filled = 0
        semantic_rows: list[tuple[dict[str, Any], str]] = []
        for track, metadata in zip(selected, metadata_rows):
            if isinstance(metadata, Exception) or not metadata:
                continue
            result = metadata.get("result", {}) or {}
            song = metadata.get("song", {}) or {}
            signal = self._build_signal(profile, track, result, song)
            track.lyric_signals = signal
            filled += 1
            description = self._description_text(song)
            if profile.meaning_required and profile.lyrical_intent and description:
                semantic_rows.append((signal, description))

        if semantic_rows:
            passages = [description for _, description in semantic_rows]
            raw_scores = await asyncio.to_thread(
                self._semantic_matcher.score,
                profile.lyrical_intent,
                passages,
            )
            if len(raw_scores) != len(semantic_rows):
                raise RuntimeError("E5 matcher returned an unexpected score count")
            relative_scores = self._relative_scores(raw_scores)
            for (signal, _), raw_score, relative_score in zip(
                semantic_rows,
                raw_scores,
                relative_scores,
            ):
                signal["semantic_score"] = round(float(raw_score), 6)
                signal["semantic_model"] = self._semantic_matcher.MODEL_ID
                signal["match_score"] = relative_score

        return {"enabled": True, "lookups": safe_limit, "filled": filled, "source": "genius"}
```

Add these helpers:

```python
    @staticmethod
    def _description_text(song: dict[str, Any]) -> str:
        return re.sub(r"\s+", " ", str(song.get("description_preview") or "")).strip()

    @staticmethod
    def _relative_scores(scores: list[float]) -> list[float]:
        if not scores:
            return []
        low = min(scores)
        high = max(scores)
        if len(scores) == 1 or high - low <= 1e-9:
            return [0.5] * len(scores)
        return [round((score - low) / (high - low), 4) for score in scores]
```

Make `_build_signal()` normalize `_description_text(song)`:

```python
        description = self._normalize_text(self._description_text(song))
```

Replace `_match_score()` with the same non-lexical metadata heuristic:

```python
    @classmethod
    def _match_score(
        cls,
        profile: IntentProfile,
        text: str,
        themes: list[str],
        sentiment: str,
        language: str,
    ) -> float:
        score = 0.0
        if profile.mood and profile.mood.lower() in text:
            score += 0.2
        if profile.activity and profile.activity.lower() in text:
            score += 0.12
        if profile.genre and any(g.lower() in text for g in profile.genre):
            score += 0.12
        if profile.language == language:
            score += 0.08
        if profile.mood in {"sad", "melancholy", "galau"} and sentiment == "sad":
            score += 0.18
        if profile.energy == "high" and any(t in themes for t in ["party", "confidence"]):
            score += 0.12
        if profile.energy == "low" and any(t in themes for t in ["calm", "heartbreak", "longing"]):
            score += 0.12
        return round(max(0.0, min(1.0, score)), 4)
```

- [ ] **Step 4: Run Genius tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_genius_client.py tests/test_embedding_service.py -q
```

Expected: all matcher and Genius tests pass.

- [ ] **Step 5: Add and verify the cached-metadata regression test**

Add a second-intent test to `tests/test_genius_client.py`. Seed profile-independent metadata in the real cache so only the E5 result changes:

```python
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
```

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_genius_client.py::test_cached_metadata_is_rescored_for_each_intent -q
```

Expected: `1 passed`; this test would fail against the former profile-bound cache.

- [ ] **Step 6: Commit Genius semantic scoring**

```powershell
git add app/services/genius_client.py tests/test_genius_client.py
git commit -m "feat: score Genius metadata with E5"
```

---

### Task 3: Pipeline Ownership and Fail-Fast Startup

**Files:**
- Create: `tests/test_embedding_startup.py`
- Modify: `app/services/pipeline.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: `E5SemanticMatcher.load() -> None`
- Produces: `RecommendationPipeline.semantic: E5SemanticMatcher`
- Produces: `RecommendationPipeline(..., semantic: E5SemanticMatcher | None = None)`

- [ ] **Step 1: Write failing lifespan tests**

Create `tests/test_embedding_startup.py`:

```python
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
```

- [ ] **Step 2: Run startup tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_embedding_startup.py -q
```

Expected: construction fails because `RecommendationPipeline` has no `semantic` parameter, or the load assertions fail because lifespan does not load E5.

- [ ] **Step 3: Own the matcher in the pipeline and load it in lifespan**

In `app/services/pipeline.py`, import `E5SemanticMatcher`, add `semantic` to the constructor, and wire it before Genius:

```python
    def __init__(
        self,
        *,
        llm: OpenRouterClient | None = None,
        spotify: SpotifyClient | None = None,
        genius: GeniusClient | None = None,
        semantic: E5SemanticMatcher | None = None,
    ) -> None:
        self.llm = llm or OpenRouterClient()
        self.profiler = ProfilerAgent(self.llm)
        self.spotify = spotify or SpotifyClient()
        self.semantic = semantic or E5SemanticMatcher()
        self.genius = genius or GeniusClient(semantic_matcher=self.semantic)
        self.ranker = RankerAgent(self.llm)
        self.presenter = PresenterAgent(self.llm)
        self.orchestrator = AgenticOrchestrator(self.llm, self.spotify, self.genius)
```

At the start of `app/main.py::lifespan`, before creating the managed HTTP client, add:

```python
    app.state.pipeline.semantic.load()
```

Keep model-load errors unhandled so FastAPI startup fails with the original exception.

- [ ] **Step 4: Run startup and focused pipeline tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_embedding_startup.py tests/test_pipeline_cache.py tests/test_genius_client.py -q
```

Expected: all focused tests pass without a model download.

- [ ] **Step 5: Commit startup wiring**

```powershell
git add app/services/pipeline.py app/main.py tests/test_embedding_startup.py
git commit -m "feat: require E5 at application startup"
```

---

### Task 4: Documentation, Dependency Install, and Real-Model Verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the production `E5SemanticMatcher` and current requirements file.
- Produces: documented setup and one verified real-model smoke result.

- [ ] **Step 1: Update active architecture and setup documentation**

Update `README.md` so it explicitly states:

```markdown
- Lyric-sensitive requests compare the preserved intent with Genius description metadata using `intfloat/multilingual-e5-small`.
- E5 is loaded during startup and the first run may download about 471 MB of model weights.
- The embedding score compares metadata descriptions only; SmartDiscover still does not retrieve or claim knowledge of full lyrics.
```

Add `Sentence Transformers + multilingual E5` to the Tech Stack and route the Mermaid pipeline through a bounded `Genius metadata + E5 semantic scoring` node before ranking.

- [ ] **Step 2: Install the pinned dependency**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Expected: installation succeeds and `sentence-transformers 5.6.0` is available. Network approval may be required.

- [ ] **Step 3: Run a real Indonesian semantic smoke comparison**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from app.services.embedding_service import E5SemanticMatcher; m=E5SemanticMatcher(); m.load(); s=m.score('memaafkan diri setelah mengalami kegagalan', ['berdamai dengan diri sendiri sesudah gagal', 'liburan ceria menikmati matahari di pantai']); print(s); assert len(s)==2 and s[0] > s[1]"
```

Expected: two scores are printed and the paraphrase score is greater than the unrelated beach description. This downloads/caches the model but makes no Spotify or Genius request.

- [ ] **Step 4: Run the complete offline suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass. Existing Starlette cookie deprecation warnings are acceptable; no test may download E5 or call Spotify.

- [ ] **Step 5: Commit documentation**

```powershell
git add README.md
git commit -m "docs: explain E5 lyric-semantic ranking"
```

---

## E5 Completion Evidence

Run and retain these outputs before starting the Supabase-removal plan:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_embedding_service.py tests/test_embedding_startup.py tests/test_genius_client.py -q
.\.venv\Scripts\python.exe -m pytest -q
rg -n "intfloat/multilingual-e5-small|sentence-transformers==5.6.0" app requirements.txt README.md
git status --short
```

The first two commands must pass. The search must show the fixed model and pinned package in active code/docs. Git status may contain only the pre-existing `.gitignore` change and generated `graphify-out/`; implementation files must be committed.
