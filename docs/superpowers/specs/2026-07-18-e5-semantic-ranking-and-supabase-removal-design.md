# E5 Semantic Ranking and Supabase Removal Design

## Goal

Improve SmartDiscover's lyric-sensitive recommendations with
`intfloat/multilingual-e5-small`, while removing the complete Supabase prompt
logging and recent-prompt autocomplete feature. The result must work and be
testable without Spotify Premium.

## Decisions

- Use `sentence-transformers==5.6.0` on the project's Python 3.12 runtime.
- Use the fixed model ID `intfloat/multilingual-e5-small`; do not add a model
  selector or vector database.
- Load the model during FastAPI lifespan startup. A missing dependency, failed
  model download, or model initialization error aborts application startup.
- Run semantic inference only for profiles where `meaning_required=true` and
  `lyrical_intent` is non-empty.
- Remove Supabase and recent-prompt autocomplete without replacement. Keep the
  existing static quick-prompt chips.
- Keep Genius evidence labelled as metadata-only. Embeddings improve comparison
  against Genius descriptions but do not imply access to full lyrics.

## Architecture

### E5 semantic matcher

A focused `E5SemanticMatcher` service owns one `SentenceTransformer` instance.
Its public behavior is deliberately small:

- `load()` creates the model and is called once during application startup.
- `score(intent, passages)` requires a loaded model and returns one cosine score
  per passage.
- The query is encoded as `query: <intent>` and each Genius description as
  `passage: <description>`.
- Encoding uses normalized embeddings, so the query-to-passage dot product is
  cosine similarity.
- One batch contains the query and every available Genius description for the
  request. Inference runs through `asyncio.to_thread` so CPU work does not block
  FastAPI's event loop.

`RecommendationPipeline` owns the matcher and passes it to `GeniusClient`.
Tests may inject a small fake matcher, following the pipeline's existing client
injection style. There is no factory, model registry, or fallback matcher.

### Genius metadata cache and scoring

The current Genius cache is keyed by track but stores a `match_score` calculated
from the active profile. That can reuse one prompt's score for a later prompt.
The cache will instead contain only profile-independent Genius result and song
metadata. `enrich_candidates()` rebuilds signals for the current profile on
every request.

For lyric-sensitive requests with at least one Genius description:

1. Fetch or retrieve profile-independent metadata for the bounded candidate set.
2. Build the ordinary metadata fields (`themes`, `sentiment`, `language`, source,
   confidence, and evidence note) for the current profile.
3. Batch-score all descriptions against `lyrical_intent` with E5.
4. Store the raw cosine value as `semantic_score` for transparency.
5. Convert the batch to a relative `match_score` using min-max normalization.
   The highest cosine becomes `1.0` and the lowest becomes `0.0`. A batch with
   one description or equal scores receives neutral `0.5`, because E5 similarity
   is useful primarily for relative ordering and should not create false absolute
   confidence.

For profiles that do not require lyric meaning, no embedding inference runs and
the existing mood, activity, genre, language, sentiment, and theme heuristic
continues to produce `match_score`. Metadata without a description retains a
zero match score and low confidence.

`RankerAgent` continues consuming `match_score` through the existing lyric bonus
and Genius confidence multiplier. This preserves the established overall weight
while making the relative lyric ordering semantic instead of lexical. The old
lyrical token-overlap helper and its stopword list become dead code and are
removed.

### Startup behavior

FastAPI lifespan loads E5 before logging that SmartDiscover is ready. Model
loading is intentionally fail-fast: the application must not silently return to
lexical matching. The model may use the device selected by Sentence Transformers;
no CUDA-specific requirement is introduced. First startup may download model
artifacts, while later startups use the Hugging Face cache.

### Supabase removal

The removal is complete across all layers:

- Delete `app/services/prompt_store.py` and its tests.
- Remove Supabase, IP-hash salt, and suggestion-rate-limit settings.
- Remove `PromptStore` construction, HTTP-client attachment, dependency wiring,
  prompt persistence, module aliases, and `/api/prompt-suggestions`.
- Remove Supabase variables from `.env.example` and all Supabase/privacy/prompt
  persistence documentation from `README.md`.
- Remove the prompt-suggestions API helper, debounce/dropdown logic, dropdown
  markup, and its CSS.
- Remove or update backend tests whose only purpose was Supabase persistence or
  the deleted suggestions endpoint.

The `/recommend` endpoint remains rate-limited and returns the same response
schema. Removing analytics must not change recommendation behavior.

## Data Flow

1. FastAPI startup loads the E5 model and attaches shared HTTP clients.
2. `ProfilerAgent` preserves lyric-sensitive text in `lyrical_intent`.
3. Spotify candidate collection and heuristic Genius preselection remain
   unchanged.
4. `GeniusClient` fetches cached or remote metadata for the selected tracks.
5. When meaning is required, one E5 batch compares the intent with every
   available description and writes per-request semantic signals.
6. The existing ranker and presenter consume those bounded, confidence-weighted
   signals.
7. `/recommend` returns directly; no prompt or client information is persisted.

## Error Handling

- Model load failures abort FastAPI startup with the original actionable error.
- Calling `score()` before `load()` raises a clear runtime error.
- Empty passages return an empty score list without inference.
- A mismatched Genius hit, missing description, or Genius network failure keeps
  the existing metadata/audio fallback behavior; these do not disable E5.
- A malformed encoder result with a count different from the passage count
  raises an error rather than assigning scores to the wrong tracks.

## Testing and Verification

- Unit-test E5 prefixes, normalized encoding request, cosine output mapping,
  empty passages, and use-before-load with a fake encoder; committed tests never
  download the model.
- Add a Genius enrichment test where a fake semantic matcher ranks a paraphrase
  above a lexically unrelated description.
- Add a regression test proving cached metadata is rescored for a second intent.
- Verify non-meaning requests do not call the matcher and title-only metadata
  retains a zero match score with low confidence.
- Verify application lifespan calls E5 `load()` and propagates load failure.
- Update endpoint and rate-limit tests to prove `/recommend` still works and
  `/api/prompt-suggestions` is absent.
- Search runtime code, tests, frontend files, active configuration, and README
  for `supabase`, `PromptStore`, `prompt-suggestions`, and deleted environment
  keys; no active integration reference may remain. Historical design and plan
  documents may retain removal rationale.
- Run the complete pytest suite using `.venv\Scripts\python.exe -m pytest -q`.
- Install dependencies and perform one local smoke comparison with the real E5
  model using Indonesian paraphrase and unrelated passages. This does not call
  Spotify or Genius.

## Success Criteria

- FastAPI cannot report ready until `intfloat/multilingual-e5-small` is loaded.
- Lyric-sensitive Genius candidates receive E5-based per-request ranking signals.
- The same cached track metadata cannot reuse a previous prompt's score.
- Non-lyric requests avoid embedding inference.
- All Supabase backend, frontend, configuration, tests, and documentation are
  removed while static quick prompts remain functional.
- Offline unit tests, the full suite, and the real-model smoke comparison pass
  without Spotify Premium.

## Non-goals

- Full-lyrics retrieval, scraping, or claims of complete song understanding.
- Fine-tuning E5, storing embeddings, approximate nearest-neighbor search, or a
  vector database.
- ONNX export, quantization, GPU-specific configuration, or a runtime model
  selector.
- Replacing removed prompt history with another database or browser storage.
