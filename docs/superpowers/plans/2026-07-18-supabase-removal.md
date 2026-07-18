# Supabase Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove SmartDiscover's Supabase prompt logging and recent-prompt autocomplete feature from backend, frontend, configuration, tests, and documentation without changing recommendation results.

**Architecture:** Delete the optional persistence path instead of replacing it. `/recommend` returns the pipeline response directly, the suggestions endpoint and dropdown disappear, and existing static quick-prompt chips remain the only prompt shortcut.

**Tech Stack:** Python 3.12, FastAPI, pytest, vanilla JavaScript, HTML, CSS.

## Global Constraints

- Remove Supabase completely; do not replace it with another database, file, browser storage, or in-memory history.
- Remove `/api/prompt-suggestions`, prompt persistence, client-IP hashing, and suggestion-specific rate limiting.
- Preserve `/recommend` rate limiting and its response schema.
- Preserve static quick-prompt chips and `bindQuickPrompts()`.
- Do not inspect, print, or edit the user's ignored `.env`; update only `.env.example`.
- Preserve the user's existing `.gitignore` modification and do not stage `graphify-out/`.
- Execute this plan only after the E5 semantic-ranking plan passes its completion evidence.

---

## File Structure

- Create `tests/test_supabase_removed.py`: acceptance checks for deleted backend and UI surfaces.
- Delete `app/services/prompt_store.py`: remove Supabase REST persistence and IP hashing.
- Delete `tests/test_prompt_store_pii.py`: remove tests for the deleted service.
- Modify `app/config.py`: remove Supabase, IP salt, and suggestions limit settings.
- Modify `app/main.py`: remove store lifecycle/dependencies, endpoint, and prompt save call.
- Modify `tests/test_recommend_schema.py`: remove persistence-only tests while retaining schema/count tests.
- Modify `tests/test_rate_limit.py`: scope documentation to `/recommend` only.
- Modify `.env.example`: remove deleted variables and analytics comments.
- Modify `web/js/main.js`: remove autocomplete behavior and unused DOM helpers.
- Modify `web/js/api.js`: remove the suggestions API call.
- Modify `web/index.html`: remove dropdown markup and its wrapper while keeping quick prompts.
- Modify `web/css/components/forms.css`: remove dropdown-only CSS.
- Modify `README.md`: remove Supabase setup, analytics privacy disclosure, and endpoint documentation.

---

### Task 1: Remove the Backend Persistence Surface

**Files:**
- Create: `tests/test_supabase_removed.py`
- Delete: `app/services/prompt_store.py`
- Delete: `tests/test_prompt_store_pii.py`
- Modify: `app/config.py`
- Modify: `app/main.py`
- Modify: `tests/test_recommend_schema.py`
- Modify: `tests/test_rate_limit.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: `/api/prompt-suggestions` returns HTTP 404.
- Produces: `Settings` has no Supabase, `ip_hash_salt`, or `rate_limit_suggestions` fields.
- Preserves: `POST /recommend` calls `RecommendationPipeline.run()` once and returns its response unchanged.

- [ ] **Step 1: Write the failing backend-removal acceptance test**

Create `tests/test_supabase_removed.py`:

```python
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def test_supabase_backend_surface_is_removed() -> None:
    assert client.get("/api/prompt-suggestions").status_code == 404
    assert not hasattr(app.state, "prompt_store")
    for name in (
        "supabase_url",
        "supabase_api_key",
        "supabase_prompt_table",
        "ip_hash_salt",
        "rate_limit_suggestions",
    ):
        assert not hasattr(settings, name)
```

- [ ] **Step 2: Run the backend acceptance test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_supabase_removed.py::test_supabase_backend_surface_is_removed -q
```

Expected: failure because the endpoint, app state, and settings still exist.

- [ ] **Step 3: Remove backend integration and configuration**

In `app/config.py`, delete these fields:

```python
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_api_key: str = Field(default="", validation_alias="SUPABASE_API_KEY")
    supabase_prompt_table: str = Field(default="prompt_logs", validation_alias="SUPABASE_PROMPT_TABLE")
    ip_hash_salt: str = Field(default="dev-only-salt", validation_alias="IP_HASH_SALT")
    rate_limit_suggestions: str = Field(default="30/minute", validation_alias="RATE_LIMIT_SUGGESTIONS")
```

In `app/main.py`:

- Remove `PromptStore` import, construction, client attachment, module alias, `get_prompt_store()`, and `/api/prompt-suggestions`.
- Reduce `/recommend` to the existing pipeline dependency only:

```python
@app.post("/recommend", response_model=RecommendResponse)
@limiter.limit(settings.rate_limit_recommend)
async def recommend(
    request: Request,
    payload: RecommendRequest,
    pipeline: RecommendationPipeline = Depends(get_pipeline),
) -> RecommendResponse:
    return await pipeline.run(payload)
```

Delete `app/services/prompt_store.py` and `tests/test_prompt_store_pii.py`.

From `tests/test_recommend_schema.py`, delete only:

```text
test_recommend_persists_prompt_without_breaking_schema
test_recommend_still_success_when_prompt_persist_fails
```

Keep `test_recommend_default_schema_and_count` and `test_recommend_custom_target_count` as the `/recommend` regression proof.

Change the first line of `tests/test_rate_limit.py` to:

```python
"""Validate input caps and rate limiting on /recommend."""
```

Remove `SUPABASE_URL`, `SUPABASE_API_KEY`, `SUPABASE_PROMPT_TABLE`, `IP_HASH_SALT`, `RATE_LIMIT_SUGGESTIONS`, and their analytics comments from `.env.example`. Keep:

```ini
# Required in production. Use a long random string (>=32 chars).
SESSION_SECRET=""

# Rate limit (slowapi syntax). Examples: "10/minute", "100/hour".
RATE_LIMIT_RECOMMEND="10/minute"
```

- [ ] **Step 4: Run backend tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_supabase_removed.py::test_supabase_backend_surface_is_removed tests/test_recommend_schema.py tests/test_rate_limit.py -q
```

Expected: all selected tests pass; `/recommend` schema and rate limit remain intact.

- [ ] **Step 5: Verify the deleted service has no backend callers**

Run:

```powershell
rg -n -i --glob '!test_supabase_removed.py' "supabase|PromptStore|SUPABASE_|IP_HASH_SALT|RATE_LIMIT_SUGGESTIONS|prompt-suggestions" app tests .env.example
```

Expected: no output and `rg` exit code `1`. The historical design/plan documents are intentionally outside this scan.

- [ ] **Step 6: Commit backend removal**

```powershell
git add app/config.py app/main.py app/services/prompt_store.py tests/test_prompt_store_pii.py tests/test_recommend_schema.py tests/test_rate_limit.py tests/test_supabase_removed.py .env.example
git commit -m "refactor: remove Supabase prompt persistence"
```

---

### Task 2: Remove Recent-Prompt Autocomplete UI

**Files:**
- Modify: `tests/test_supabase_removed.py`
- Modify: `web/js/main.js`
- Modify: `web/js/api.js`
- Modify: `web/index.html`
- Modify: `web/css/components/forms.css`

**Interfaces:**
- Produces: no prompt-history request, dropdown, keyboard handler, or dropdown CSS remains.
- Preserves: `#quickPrompts`, the three static `.chip` buttons, and `bindQuickPrompts()`.

- [ ] **Step 1: Add the failing static UI acceptance test**

Append to `tests/test_supabase_removed.py`:

```python
def test_prompt_history_ui_is_removed_but_static_quick_prompts_remain() -> None:
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    main_js = (ROOT / "web/js/main.js").read_text(encoding="utf-8")
    api_js = (ROOT / "web/js/api.js").read_text(encoding="utf-8")
    forms_css = (ROOT / "web/css/components/forms.css").read_text(encoding="utf-8")

    assert "promptSuggestions" not in html
    assert "bindPromptSuggestions" not in main_js
    assert "promptSuggestions" not in api_js
    assert "prompt-suggestions" not in forms_css
    assert 'id="quickPrompts"' in html
    assert "bindQuickPrompts();" in main_js
```

- [ ] **Step 2: Run the UI acceptance test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_supabase_removed.py::test_prompt_history_ui_is_removed_but_static_quick_prompts_remain -q
```

Expected: failure because the dropdown and autocomplete code still exist.

- [ ] **Step 3: Delete autocomplete code while preserving static chips**

In `web/js/main.js`:

- Change the first import to:

```javascript
import { $ } from "./utils/dom.js";
```

- Delete the complete `bindPromptSuggestions()` function.
- Delete only the `bindPromptSuggestions();` call from `boot()`; keep `bindQuickPrompts();`.

In `web/js/api.js`, delete:

```javascript
export async function promptSuggestions(q) {
  const params = new URLSearchParams({ q: q || "" });
  return jsonFetch(`/api/prompt-suggestions?${params.toString()}`);
}
```

In `web/index.html`, replace the textarea wrapper with the textarea alone:

```html
<div class="field">
  <label class="field__label" for="intentInput" id="intentLabel">Apa mood atau aktivitasmu?</label>
  <textarea id="intentInput" class="textarea" rows="3" placeholder="contoh: lagu sedih pas nge-bug jam 2 pagi..." required></textarea>
</div>
```

In `web/css/components/forms.css`, delete the complete block from `/* Prompt suggestions dropdown */` through `.prompt-suggestion-item.is-active`. Keep the following `/* Quick prompt chips */` block unchanged.

- [ ] **Step 4: Run the UI acceptance test and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_supabase_removed.py -q
```

Expected: both backend and UI removal tests pass.

- [ ] **Step 5: Commit frontend removal**

```powershell
git add tests/test_supabase_removed.py web/js/main.js web/js/api.js web/index.html web/css/components/forms.css
git commit -m "refactor: remove prompt history autocomplete"
```

---

### Task 3: Remove Supabase Documentation and Audit the Repository

**Files:**
- Modify: `README.md`

**Interfaces:**
- Produces: active documentation describes no Supabase environment, persistence, privacy flow, or suggestions endpoint.
- Preserves: E5 metadata-only disclosure and Spotify OAuth/cookie documentation.

- [ ] **Step 1: Remove obsolete README sections and variables**

From the setup environment example and reference table in `README.md`, remove:

```text
SUPABASE_URL
SUPABASE_API_KEY
SUPABASE_PROMPT_TABLE
IP_HASH_SALT
RATE_LIMIT_SUGGESTIONS
```

Delete the `### Privacy disclosure` subsection describing prompt text, IP hash, User-Agent, and Supabase persistence. Delete the `/api/prompt-suggestions` row from the API endpoint table. Keep `RATE_LIMIT_RECOMMEND`, Spotify cookie behavior, and the E5 metadata-only statement.

- [ ] **Step 2: Run the active-source Supabase audit**

Run:

```powershell
rg -n -i --glob '!test_supabase_removed.py' "supabase|PromptStore|prompt-suggestions|promptSuggestions|SUPABASE_|IP_HASH_SALT|RATE_LIMIT_SUGGESTIONS" app tests web .env.example README.md requirements.txt
```

Expected: no output and `rg` exit code `1`. Historical files under `docs/superpowers/` are excluded because they retain design rationale.

- [ ] **Step 3: Verify static quick prompts still exist**

Run:

```powershell
rg -n 'id="quickPrompts"|bindQuickPrompts\(\)' web/index.html web/js/main.js
```

Expected: one `quickPrompts` container, the function definition, and its boot call are shown.

- [ ] **Step 4: Run the complete test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass. Existing Starlette cookie deprecation warnings are acceptable.

- [ ] **Step 5: Commit documentation cleanup**

```powershell
git add README.md
git commit -m "docs: remove Supabase integration guidance"
```

---

## Supabase Removal Completion Evidence

Run and retain these outputs:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_supabase_removed.py tests/test_recommend_schema.py tests/test_rate_limit.py -q
.\.venv\Scripts\python.exe -m pytest -q
rg -n -i --glob '!test_supabase_removed.py' "supabase|PromptStore|prompt-suggestions|promptSuggestions|SUPABASE_|IP_HASH_SALT|RATE_LIMIT_SUGGESTIONS" app tests web .env.example README.md requirements.txt
rg -n 'id="quickPrompts"|bindQuickPrompts\(\)' web/index.html web/js/main.js
git status --short
```

The focused and full test suites must pass. The Supabase search must produce no output. The quick-prompt search must show retained static behavior. Git status may contain only the pre-existing `.gitignore` change and generated `graphify-out/`; implementation files must be committed.
