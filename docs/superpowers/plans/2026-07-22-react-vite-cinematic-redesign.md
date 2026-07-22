# React + Vite Cinematic Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace SmartDiscover's vanilla frontend with a React + Vite + TypeScript cinematic prompt-to-results experience while preserving every existing FastAPI, Spotify, recommendation, refinement, preview, i18n, and diagnostic behavior.

**Architecture:** A single React application in `frontend/` owns the four UI states (`idle`, `loading`, `success`, `error`) and calls the existing relative FastAPI endpoints. Vite proxies those endpoints during development and writes `frontend/dist` for production; FastAPI remains the only production server and serves the built entry point and assets.

**Tech Stack:** React, Vite, TypeScript, Tailwind CSS, shadcn/ui with Radix, Motion, Vitest, Testing Library, FastAPI, pytest.

## Global Constraints

- Work only on branch `codex/react-vite-redesign` until the verified merge step.
- Preserve `/recommend`, `/refine`, `/auth/*`, `/create-playlist`, `/llm/health`, and `/spotify/health` contracts.
- Preserve Indonesian as the initial locale and the ID/EN switch.
- Preserve Spotify cookie security; no token may be stored in React or browser storage.
- Use local React state and focused hooks; do not add Redux, React Router, Next.js, or another animation/component system.
- Use shadcn/ui with the Radix base.
- Use Motion only for the hero-to-compact transition and result entrances.
- Preserve the near-black canvas, warm paper cards, coral accent, Fraunces headings, Inter body type, logo, and 44 px touch targets.
- Enter submits the main composer; Shift+Enter creates a newline.
- Loading shows the progress journey but no fake recommendation cards.
- Respect `prefers-reduced-motion` for transition, scroll, and stagger behavior.
- Keep `graphify-out/` untracked and untouched.
- Every behavior change follows red-green-refactor; configuration-only scaffolding is verified by typecheck/build instead.

---

### Task 1: Scaffold the React/Vite/shadcn Testable Shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/package-lock.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/components.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/App.test.tsx`
- Create: `frontend/src/components/ui/*` through the shadcn CLI
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Node.js 24+, npm, existing FastAPI at `http://127.0.0.1:8000`.
- Produces: `npm run test`, `npm run typecheck`, and `npm run build`; `@/*` alias; shadcn primitives; Vite proxy configuration.

- [ ] **Step 1: Scaffold Vite and install only the approved dependencies**

Run from the repository root:

```powershell
npm create vite@latest frontend -- --template react-ts
Set-Location frontend
npm install
npm install motion
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
npx shadcn@latest init -d --base radix
npx shadcn@latest add button textarea card collapsible dialog alert badge label select input
```

Expected: `frontend/package-lock.json` exists; shadcn source files are under `frontend/src/components/ui/`; no dependency is added for routing or global state.

- [ ] **Step 2: Configure scripts, Vite proxying, and the test environment**

Set these scripts in `frontend/package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc -b --pretty false",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

Use this `frontend/vite.config.ts` shape:

```ts
/// <reference types="vitest/config" />
import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

const backend = "http://127.0.0.1:8000"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    proxy: Object.fromEntries(
      ["/recommend", "/refine", "/auth", "/create-playlist", "/llm", "/spotify"]
        .map((route) => [route, { target: backend, changeOrigin: false }]),
    ),
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
    restoreMocks: true,
  },
})
```

Create `frontend/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest"
```

Add these entries to `.gitignore`:

```gitignore
node_modules/
frontend/dist/
```

- [ ] **Step 3: Write the failing shell test**

Create `frontend/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import App from "./App"

describe("App", () => {
  it("renders the SmartDiscover application landmark", () => {
    render(<App />)
    expect(screen.getByRole("main", { name: /smartdiscover/i })).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Run the test to verify RED**

Run: `npm test -- App.test.tsx`

Expected: FAIL because the scaffolded `App` has no named SmartDiscover main landmark.

- [ ] **Step 5: Implement the smallest shell and theme entry**

Replace `frontend/src/App.tsx` with:

```tsx
export default function App() {
  return <main aria-label="SmartDiscover">SmartDiscover</main>
}
```

Keep `frontend/src/main.tsx` as the strict-mode render entry and import `./index.css`. Configure `frontend/index.html` with the SmartDiscover title, logo favicon, Fraunces and Inter font links, and `<div id="root"></div>`.

- [ ] **Step 6: Verify GREEN, typecheck, and build**

Run:

```powershell
npm test -- App.test.tsx
npm run typecheck
npm run build
```

Expected: one passing test, zero TypeScript errors, and a successful `frontend/dist` build.

- [ ] **Step 7: Commit the scaffold**

```powershell
git add .gitignore frontend
git commit -m "build: scaffold React Vite frontend"
```

---

### Task 2: Define API Contracts, Error Semantics, Formatting, and i18n

**Files:**
- Create: `frontend/src/types/recommendation.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/api.test.ts`
- Create: `frontend/src/lib/format.ts`
- Create: `frontend/src/lib/format.test.ts`
- Create: `frontend/src/lib/i18n.tsx`
- Create: `frontend/src/lib/i18n.test.tsx`

**Interfaces:**
- Consumes: Pydantic models in `app/models.py` and endpoint behavior in `web/js/api.js`.
- Produces: `RecommendRequest`, `RefineRequest`, `RecommendResponse`, `RecommendationItem`, `IntentProfile`, `ApiError`, typed request functions, `trackIdFromUrl`, formatting helpers, `I18nProvider`, and `useI18n()`.

- [ ] **Step 1: Write failing API and formatting tests**

`frontend/src/lib/api.test.ts` must assert that `recommend()` posts JSON to `/recommend`, includes `Content-Type: application/json`, and converts a JSON `{detail}` failure into an `ApiError` with the response status. `frontend/src/lib/format.test.ts` must assert:

```ts
expect(trackIdFromUrl("https://open.spotify.com/track/abc123?si=x")).toBe("abc123")
expect(formatPercent(0.876, 0)).toBe("88%")
expect(formatDuration(65)).toBe("1:05")
```

Use `vi.stubGlobal("fetch", vi.fn())` with real `Response` values, not a mock of `recommend()` itself.

- [ ] **Step 2: Run tests to verify RED**

Run: `npm test -- src/lib/api.test.ts src/lib/format.test.ts`

Expected: FAIL because the typed client and helpers do not exist.

- [ ] **Step 3: Implement exact API and type boundaries**

Define these public shapes in `frontend/src/types/recommendation.ts`:

```ts
export type AgenticMode = "auto" | "agentic" | "linear"

export interface IntentProfile {
  mood: string
  activity: string
  genre: string[]
  energy: "low" | "medium" | "high"
  language: "id" | "en"
  locale: string
  strict_locale: boolean
  confidence: number
  target_audio: Record<string, number>
  seed_genres: string[]
  decade: string
  lyrical_intent: string
  meaning_required: boolean
}

export interface RecommendationItem {
  rank: number
  title: string
  artist: string
  track_id: string
  spotify_url: string
  preview_url: string
  why: string
  score: number
  audio_features?: Record<string, number> | null
  lyric_signals?: Record<string, unknown> | null
}

export interface RecommendResponse {
  summary: Record<string, unknown> & { intent_text?: string; target_count?: number; returned_count?: number }
  intent_profile: IntentProfile
  query_strategy: Record<string, unknown>
  recommendations: RecommendationItem[]
  quality_notes: Record<string, unknown> & {
    stage_ms?: Record<string, number>
    quality_warnings?: string[]
    llm_enabled?: boolean
    llm_profiler_used?: boolean
    llm_ranker_used?: boolean
    llm_presenter_used?: boolean
    agent_loop_enabled?: boolean
    agentic?: Record<string, unknown>
  }
}
```

Implement `jsonFetch<T>()`, `recommend()`, `refine()`, `authStatus()`, `createPlaylist()`, `llmHealth()`, and `spotifyHealth()` in `api.ts`. Always use relative URLs; pass `credentials: "include"` for auth status and playlist creation; expose `ApiError.status` and parsed response data.

- [ ] **Step 4: Verify API/format GREEN**

Run: `npm test -- src/lib/api.test.ts src/lib/format.test.ts`

Expected: PASS.

- [ ] **Step 5: Write the failing i18n test**

The test must render a probe inside `I18nProvider`, verify Indonesian `heroTitle` initially, click a button that calls `setLanguage("en")`, verify English `heroTitle`, confirm `document.documentElement.lang === "en"`, and confirm `localStorage.smartdiscover_lang === "en"`.

- [ ] **Step 6: Run i18n test to verify RED**

Run: `npm test -- src/lib/i18n.test.tsx`

Expected: FAIL because the provider does not exist.

- [ ] **Step 7: Implement the provider and migrate every current copy key**

Move both complete locale dictionaries from `web/js/i18n.js` into typed `Record<Locale, Messages>` data. Keep current copy values, add only the compact-search and cinematic-loading labels required by the approved design, implement `{variable}` interpolation, initialize from `smartdiscover_lang`, and synchronize the `<html lang>` attribute.

- [ ] **Step 8: Verify all Task 2 tests and commit**

Run:

```powershell
npm test -- src/lib
npm run typecheck
git add frontend/src/types frontend/src/lib
git commit -m "feat: add typed frontend contracts and i18n"
```

Expected: all Task 2 tests pass and typecheck exits 0.

---

### Task 3: Build the Cinematic App Shell and Prompt Composer

**Files:**
- Create: `frontend/src/components/AppHeader.tsx`
- Create: `frontend/src/components/PromptComposer.tsx`
- Create: `frontend/src/components/PromptComposer.test.tsx`
- Create: `frontend/src/components/HealthStatus.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Consumes: shadcn Button/Textarea/Collapsible/Select/Input/Label, Motion, `useI18n()`, `AgenticMode`.
- Produces: `PromptValues`, `PromptComposerProps`, the `idle` hero and `compact` prompt variants, header language/Spotify controls, cinematic design tokens.

- [ ] **Step 1: Write failing prompt interaction tests**

Cover these behaviors with Testing Library and `userEvent`:

```tsx
it("submits with Enter but keeps Shift+Enter for a newline")
it("fills the textarea from a quick prompt")
it("keeps advanced settings collapsed by default")
it("uses 15 and auto as the default advanced values")
it("renders compact mode without losing the prompt value")
```

The submit assertion must receive `{ text, targetCount: 15, agenticMode: "auto" }`; a whitespace-only prompt must show the localized validation message and not call `onSubmit`.

- [ ] **Step 2: Run prompt tests to verify RED**

Run: `npm test -- src/components/PromptComposer.test.tsx`

Expected: FAIL because `PromptComposer` does not exist.

- [ ] **Step 3: Implement the prompt component with native form semantics**

Use this public interface:

```ts
export interface PromptValues {
  text: string
  targetCount: number
  agenticMode: AgenticMode
}

interface PromptComposerProps {
  mode: "hero" | "compact"
  busy: boolean
  values: PromptValues
  onValuesChange: (values: PromptValues) => void
  onSubmit: (values: PromptValues) => void
}
```

Use a `<form>`, visible `<Label>`, controlled `<Textarea>`, three localized quick-prompt buttons, a shadcn `Collapsible` for target count/agentic mode/health, and one submit `Button`. Handle Enter in the textarea only when Shift is not held and IME composition is inactive. Give the hero and compact surfaces the same Motion `layoutId="prompt-composer"`.

- [ ] **Step 4: Implement the app shell and approved styling**

`AppHeader` contains only brand/logo, language controls, and Spotify connection. `index.css` must define Tailwind theme variables for the approved canvas/paper/coral colors, Fraunces/Inter families, focus ring, 44 px controls, responsive 360 px layout, and reduced-motion fallback. Avoid a second CSS architecture under `web/css`.

- [ ] **Step 5: Verify prompt GREEN and responsive static contracts**

Run:

```powershell
npm test -- src/components/PromptComposer.test.tsx src/App.test.tsx
npm run typecheck
npm run build
```

Expected: tests pass, build exits 0, and generated CSS has no compile errors.

- [ ] **Step 6: Commit the shell and composer**

```powershell
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/index.css frontend/src/components
git commit -m "feat: add cinematic prompt composer"
```

---

### Task 4: Implement the Request Lifecycle and Loading Journey

**Files:**
- Create: `frontend/src/hooks/useRecommendation.ts`
- Create: `frontend/src/hooks/useRecommendation.test.tsx`
- Create: `frontend/src/components/LoadingJourney.tsx`
- Create: `frontend/src/components/LoadingJourney.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `recommend()`, `RecommendResponse`, `PromptValues`, `useReducedMotion()`.
- Produces: `ViewState = "idle" | "loading" | "success" | "error"`, request result/error, four-stage progress, hero-to-compact transition, smooth scroll.

- [ ] **Step 1: Write failing request-lifecycle tests**

Mock only `@/lib/api` at the network boundary. Assert:

```tsx
it("moves from idle to loading and renders the compact prompt")
it("scrolls the loading journey into view when motion is allowed")
it("does not request smooth scrolling when reduced motion is enabled")
it("enters success with the resolved response")
it("enters error while preserving prompt values")
it("ignores a duplicate submit while a request is active")
```

Use a deferred Promise so the loading state is observable before resolution.

- [ ] **Step 2: Run lifecycle tests to verify RED**

Run: `npm test -- src/hooks/useRecommendation.test.tsx src/App.test.tsx`

Expected: FAIL because the hook and transitions do not exist.

- [ ] **Step 3: Implement the focused hook**

Expose:

```ts
interface RecommendationState {
  view: ViewState
  result: RecommendResponse | null
  error: string
}

function useRecommendation(): RecommendationState & {
  submit: (values: PromptValues) => Promise<void>
  replaceResult: (result: RecommendResponse) => void
}
```

Trim and validate before calling the API, map `targetCount` to `target_count` and `agenticMode` to `agentic_mode`, prevent duplicate active requests, preserve the previous prompt in `App`, and expose a plain error message without a stack trace.

- [ ] **Step 4: Implement the four-stage loading component**

Use the localized stages `profiler`, `search`, `ranker`, and `presenter`. While loading, advance optimistically with one timer and remain on the final stage until the response arrives. Clear timers on unmount/error. Use a semantic ordered list and `role="status"`; animation is decorative and hidden from assistive technology.

- [ ] **Step 5: Wire transition and scroll behavior in App**

Render hero mode only in `idle`; render compact mode for `loading`, `success`, and `error`. After the compact layout mounts, call `loadingRef.current?.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" })`. On error, keep the compact prompt editable and show shadcn `Alert`.

- [ ] **Step 6: Verify GREEN and commit**

```powershell
npm test -- src/hooks/useRecommendation.test.tsx src/components/LoadingJourney.test.tsx src/App.test.tsx
npm run typecheck
npm run build
git add frontend/src/hooks frontend/src/components/LoadingJourney* frontend/src/App*
git commit -m "feat: add prompt loading transition"
```

---

### Task 5: Render Results, Song Cards, Details, and Single-Active Preview

**Files:**
- Create: `frontend/src/components/ResultsSection.tsx`
- Create: `frontend/src/components/ResultsSection.test.tsx`
- Create: `frontend/src/components/IntentSummary.tsx`
- Create: `frontend/src/components/SongCard.tsx`
- Create: `frontend/src/components/SongCard.test.tsx`
- Create: `frontend/src/components/TrackDetailDialog.tsx`
- Create: `frontend/src/hooks/useAudioPreview.ts`
- Create: `frontend/src/hooks/useAudioPreview.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `RecommendResponse`, `RecommendationItem`, shadcn Card/Dialog/Badge/Collapsible, Motion stagger, `useI18n()`.
- Produces: intent summary, ordered recommendation list, secondary audio/lyric metadata, one active audio preview, accessible detail dialog.

- [ ] **Step 1: Write failing result and card tests**

Use one deterministic `RecommendResponse` fixture with two tracks. Assert that rank/title/artist/reason render in API order; the empty array shows the broaden-prompt message; audio detail remains collapsed; a missing preview renders a disabled button; opening Details shows score, preview availability, reason, optional lyric summary, and Spotify link.

- [ ] **Step 2: Write the failing audio ownership test**

Stub `globalThis.Audio` with instances that record `play()` and `pause()`. Start track A, then track B, and assert A was paused before B played. Assert toggling active track B pauses it and clears active state.

- [ ] **Step 3: Run tests to verify RED**

Run: `npm test -- src/components/ResultsSection.test.tsx src/components/SongCard.test.tsx src/hooks/useAudioPreview.test.tsx`

Expected: FAIL because the result components and hook do not exist.

- [ ] **Step 4: Implement intent summary and result ordering**

Show original prompt, mood, activity, returned count, basic/enhanced matching, and confidence. Render actions before warnings and recommendations. Use a Motion parent/child variant with a 0.08 second stagger; when reduced motion is active, render the same DOM order without initial transforms.

- [ ] **Step 5: Implement card/detail/preview behavior**

Each card displays zero-padded rank, title, artist, reason fallback, preview control, Spotify link, and details button. Secondary disclosure shows match percentage, energy, valence, tempo, and lyric signal when present. `useAudioPreview` owns the single `Audio` instance and animation frame, stops playback on new results/unmount, reports elapsed time, and converts playback errors to the localized unavailable state.

- [ ] **Step 6: Verify GREEN and commit**

```powershell
npm test -- src/components/ResultsSection.test.tsx src/components/SongCard.test.tsx src/hooks/useAudioPreview.test.tsx
npm run typecheck
npm run build
git add frontend/src/components frontend/src/hooks/useAudioPreview*
git commit -m "feat: add animated recommendation results"
```

---

### Task 6: Restore Refine, OAuth, Playlist Export, Quality Notices, and Diagnostics

**Files:**
- Create: `frontend/src/components/RefineBar.tsx`
- Create: `frontend/src/components/RefineBar.test.tsx`
- Create: `frontend/src/components/ExportActions.tsx`
- Create: `frontend/src/components/ExportActions.test.tsx`
- Create: `frontend/src/components/QualityAlerts.tsx`
- Create: `frontend/src/components/DiagnosticsPanel.tsx`
- Create: `frontend/src/hooks/useSpotifySession.ts`
- Create: `frontend/src/hooks/useSpotifySession.test.tsx`
- Create: `frontend/src/lib/playlist.ts`
- Create: `frontend/src/lib/playlist.test.ts`
- Modify: `frontend/src/components/AppHeader.tsx`
- Modify: `frontend/src/components/ResultsSection.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `refine()`, `authStatus()`, `createPlaylist()`, latest result/prompt/settings, `ApiError`, existing `quality_notes` keys.
- Produces: refined replacement results, Spotify connected state, cookie-authenticated playlist creation, quality warnings, collapsed diagnostics.

- [ ] **Step 1: Write failing Spotify and playlist helper tests**

Assert `useSpotifySession` calls `/auth/status`, maps a failed status check to disconnected, and removes a legacy `?token=` query parameter. Assert playlist helpers generate `SmartDiscover - <activity-or-genre-or-prompt> - YYYY-MM-DD`, cap the prompt portion, and extract track IDs from either `track_id` or the Spotify URL.

- [ ] **Step 2: Write failing refine/export component tests**

For refinement, assert a text shorter than three characters is rejected and a valid request sends `previous_profile`, all current IDs, `refinement_text`, prior target count, and current agentic mode; the resolved response replaces the displayed results. For export, assert disconnected users navigate to `/auth/login`, connected users call `/create-playlist`, success renders an external playlist link, and a 401 marks Spotify disconnected with an actionable message.

- [ ] **Step 3: Run tests to verify RED**

Run: `npm test -- src/hooks/useSpotifySession.test.tsx src/lib/playlist.test.ts src/components/RefineBar.test.tsx src/components/ExportActions.test.tsx`

Expected: FAIL because these modules do not exist.

- [ ] **Step 4: Implement session and actions without exposing tokens**

Keep only `{ connected, expiresAt }` in React state. Login uses `window.location.assign("/auth/login")`; playlist API requests use browser cookies via `credentials: "include"`. A 401 clears only React's connection indicator. Refinement replaces the latest result and source prompt but retains the compact prompt/search settings.

- [ ] **Step 5: Implement quality and diagnostic disclosure**

Map `demo_catalog`, `basic_matching`, `low_profile_confidence`, `candidate_pool_small`, and `low_average_score` to localized copy. Add demo/basic notices from Spotify status and `llm_enabled`. Inside one collapsed shadcn `Collapsible`, show stage milliseconds, LLM usage flags, agentic requested/effective mode, fallback reason, cache hits, iterations, tools, trace, and refined-from metadata when present.

- [ ] **Step 6: Verify GREEN, full frontend suite, and commit**

```powershell
npm test
npm run typecheck
npm run build
git add frontend/src
git commit -m "feat: restore frontend feature parity"
```

Expected: all frontend tests pass, no type errors, and build exits 0.

---

### Task 7: Serve the Vite Build from FastAPI and Retire the Vanilla Frontend

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_frontend_contract.py`
- Modify: `tests/test_supabase_removed.py`
- Delete: `web/index.html`
- Delete: `web/js/**`
- Delete: `web/css/**`
- Move/reuse: `web/assets/logo.svg` -> `frontend/src/assets/logo.svg`

**Interfaces:**
- Consumes: `frontend/dist/index.html`, `frontend/dist/assets/*`.
- Produces: FastAPI `/` response for the built app, `/assets/*` static mount, a clear 503 when the frontend has not been built.

- [ ] **Step 1: Write failing FastAPI static-serving tests first**

Replace implementation-detail assertions in `tests/test_frontend_contract.py` with source/build contracts:

```py
def test_frontend_stack_and_scripts_are_declared() -> None:
    package = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    assert {"react", "motion"} <= package["dependencies"].keys()
    assert {"build", "typecheck", "test"} <= package["scripts"].keys()

def test_dashboard_serves_built_index_or_clear_build_error() -> None:
    response = client.get("/")
    assert response.status_code in {200, 503}
    if response.status_code == 503:
        assert "npm run build" in response.text
```

Add a temp-directory unit test for the 200 branch by monkeypatching `FRONTEND_DIST`, writing `index.html`, and asserting the response contains the sentinel markup. Update `test_supabase_removed.py` to scan all UTF-8 files under `frontend/src` for the removed prompt-history artifacts and to assert the three static quick prompts remain in React source.

- [ ] **Step 2: Run targeted pytest to verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\test_frontend_contract.py tests\test_supabase_removed.py
```

Expected: FAIL because FastAPI still serves `web/index.html` and the old tests/source layout remain.

- [ ] **Step 3: Implement the minimum static build integration**

In `app/main.py`, define absolute paths from the repository root:

```py
ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
```

Mount `/assets` with `StaticFiles(directory=FRONTEND_DIST / "assets", check_dir=False)`. Make `/` return `FileResponse(FRONTEND_DIST / "index.html")` when present, otherwise return a `PlainTextResponse` with status 503 and the exact action `cd frontend && npm install && npm run build`. Do not mount a catch-all route because the app has no router.

- [ ] **Step 4: Build, remove vanilla sources, and verify targeted GREEN**

Run `npm run build` from `frontend/`, then remove the tracked vanilla HTML/JS/CSS only after the build succeeds. Preserve the logo by importing the moved SVG through React/Vite.

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\test_frontend_contract.py tests\test_supabase_removed.py
npm test
npm run typecheck
npm run build
```

Expected: targeted Python tests pass, frontend suite passes, and build exits 0.

- [ ] **Step 5: Commit the runtime switch**

```powershell
git add app/main.py tests frontend .gitignore
git add -u web
git commit -m "feat: serve React frontend from FastAPI"
```

---

### Task 8: Document, Verify End-to-End, Merge, and Clean Up

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md` only if it currently describes the vanilla frontend boundary
- Verify: all changed files

**Interfaces:**
- Consumes: complete feature branch.
- Produces: reproducible setup instructions, full automated evidence, desktop/mobile browser evidence, merged `main`, deleted feature branch.

- [ ] **Step 1: Update setup and architecture documentation**

Document two-terminal development:

```powershell
# terminal 1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# terminal 2
Set-Location frontend
npm install
npm run dev
```

Document production/local integrated serving:

```powershell
Set-Location frontend
npm ci
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

State that Spotify OAuth is still handled by FastAPI and browser cookies; no frontend token variable is required.

- [ ] **Step 2: Run fresh complete automated verification**

Run from `frontend/`:

```powershell
npm test
npm run typecheck
npm run build
```

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
git diff --check
git status --short
```

Expected: all frontend tests pass, typecheck/build exit 0, all 81 existing Python tests plus new frontend-contract tests pass, diff check is clean, and only `graphify-out/` remains unrelated/untracked.

- [ ] **Step 3: Verify the complete UI in a real browser**

Start FastAPI and Vite in hidden background processes. Verify at desktop and 360 px mobile widths:

- initial hero prompt and hidden results;
- Enter versus Shift+Enter;
- loading journey and hero-to-compact transition;
- smooth scroll and reduced-motion fallback;
- successful staggered cards;
- empty and request-error states;
- language switch;
- preview exclusivity and unavailable preview;
- detail dialog keyboard close;
- refinement;
- Spotify disconnected/login action;
- quality and diagnostic disclosure;
- no horizontal overflow or console errors.

Use a stubbed browser response only for deterministic success/error UI states; make one live FastAPI health request to verify proxying.

- [ ] **Step 4: Commit documentation and final fixes**

```powershell
git add README.md docs/architecture.md frontend app tests
git commit -m "docs: document React frontend workflow"
```

Omit `docs/architecture.md` from the command if no change was required.

- [ ] **Step 5: Re-run verification on the final feature commit**

Repeat the full commands from Step 2 and read their complete output. Do not merge on warnings that indicate a broken build, test failure, accessibility regression, console error, or uncommitted intended change.

- [ ] **Step 6: Merge exactly as requested and verify the merged result**

```powershell
git switch main
git merge --no-ff codex/react-vite-redesign
Set-Location frontend
npm test
npm run typecheck
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Expected: merge succeeds and every verification command passes on `main`.

- [ ] **Step 7: Delete the merged feature branch**

```powershell
git branch -d codex/react-vite-redesign
git status --short --branch
```

Expected: branch deletion succeeds; current branch is `main`; only pre-existing unrelated `graphify-out/` remains untracked.
