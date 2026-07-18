<div align="center">
  <img src="web/assets/logo.svg" alt="SmartDiscover Logo" width="170" />
  <h1>SmartDiscover</h1>
  <p><strong>Multi-Agent Music Discovery Assistant for Spotify</strong></p>

  <p>
    <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-306998?style=for-the-badge&logo=python&logoColor=white" />
    <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0F766E?style=for-the-badge&logo=fastapi&logoColor=white" />
    <img alt="Spotify API" src="https://img.shields.io/badge/Spotify_API-1DB954?style=for-the-badge&logo=spotify&logoColor=white" />
    <img alt="OpenRouter" src="https://img.shields.io/badge/OpenRouter-LLM-111827?style=for-the-badge" />
  </p>
</div>

---

> "I need calm and focused music for late-night study sessions."
>
> SmartDiscover transforms natural language prompts into relevant, ranked music recommendations that are ready to become a playlist.

## Why SmartDiscover

SmartDiscover is a multi-agent music discovery pipeline with optional agentic orchestration using LLM tool-calling. Instead of relying on literal keyword matching alone, the pipeline splits the process into intent analysis, candidate retrieval, ranking, and result presentation so recommendations feel more natural and contextual.

| Core Value | Impact |
|---|---|
| Multi-agent pipeline | More targeted results than a single-step prompt |
| Spotify integration | Real-time candidate tracks from Spotify's catalog |
| Context-based ranking | Better alignment with user mood and activity |
| Preview-aware retrieval | Better chance to get playable 30s previews |
| Playlist-ready output | Recommendations can be executed immediately |

## Agentic Architecture

```mermaid
flowchart TD
  A[User Prompt] --> B[1. Profiler Agent<br/>hybrid: heuristic + LLM<br/>JSON-mode + few-shot]
  B --> C[2. Spotify Discovery Agent<br/>recommendations + search<br/>+ audio features + artist genres]
  C --> O{agentic_mode + AGENT_LOOP_ENABLED?}
  O -- yes --> L[Orchestrator Agent<br/>tool-use loop max 3 iter:<br/>request_more_candidates,<br/>filter_by_audio,<br/>request_audio_features,<br/>finalize]
  O -- no --> D
  L --> D[3. Ranker Agent<br/>rich context: audio + genres<br/>min-output guard<br/>artist diversity]
  D --> E[4. Presenter Agent<br/>LLM-generated 'why' per track<br/>or template fallback]
  E --> F[/recommend response]
  F -. user types 'lebih upbeat' .-> R[/refine endpoint<br/>stateless re-profile + re-rank/]
  R --> F
```

### 1. Profiler Agent

- Hybrid: heuristic detector runs first (high precision for Indonesian genres), LLM extracts richer signals.
- Outputs `IntentProfile`: mood, activity, genre, energy, language, locale, strict_locale, **confidence**, **target_audio** (numeric audio targets), **seed_genres** (Spotify-canonical), decade.
- LLM call uses `response_format=json_object` + 4 few-shot examples; low-confidence results trigger one retry.
- Heuristic genre & locale findings are merged with LLM output (heuristic acts as floor; LLM cannot drop them).

### 2. Spotify Discovery Agent

- Tries `GET /v1/recommendations` first when `seed_genres` resolve against `available-genre-seeds`.
- Supplements with playlist + adaptive search when shortfall.
- Enriches every candidate with `GET /v1/audio-features` (tempo, energy, valence, danceability, acousticness, instrumentalness, loudness) and `GET /v1/artists` (artist genres) — all batched and parallel.
- Dynamic `market` derived from intent locale.

### 3. Orchestrator Agent (opt-in / runtime selectable)

- Activated when `AGENT_LOOP_ENABLED=true` or when a request sends `agentic_mode="agentic"`.
- Tool-use loop via OpenRouter function calling: `request_more_candidates`, `filter_by_audio`, `request_audio_features`, `request_lyric_signals`, `finalize`.
- Hard limits: 3 iterations, 30s wall, bounded candidate pool, validated tool inputs, automatic fallback on failure.
- Every response includes `quality_notes.agentic` with requested/effective mode, status, iteration count, tool path, trace summaries, finalized flag, and fallback reason.

### 4. Ranker Agent

- Sends LLM **rich context**: audio features + artist genres per candidate (no longer guesses from track name).
- **Min-output guard**: if LLM ranks fewer than `top_k`, fills from heuristic-scored remainder.
- **Artist diversity**: max 2 tracks per artist when alternatives exist.
- Heuristic fallback uses Euclidean distance between candidate audio features and `profile.target_audio`.

### 5. Presenter Agent

- Generates a unique `why` sentence per track in **one** batched LLM call when the ranker did not supply reasons.
- Language-aware (id / en).
- Falls back to deterministic template when LLM is disabled.

### 6. `/refine` (multi-turn)

- Stateless: client posts `{previous_profile, previous_track_ids, refinement_text, agentic_mode?}`.
- Pipeline merges previous intent + refinement, re-runs Spotify discovery + ranker, and always excludes already-seen track ids.

---

## Quick Setup

### 1) Create an App in Spotify Developer

1. Open https://developer.spotify.com/dashboard.
2. Create a new application.
3. Add the following Redirect URI:

```text
http://127.0.0.1:8000/auth/callback
```

4. Save your `Client ID` and `Client Secret`.

### 2) Clone the Repository and Install Dependencies

```powershell
git clone https://github.com/wahyu-shiregaru/SmartDiscover.git
cd SmartDiscover

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
Copy-Item .env.example .env
```

For macOS/Linux:

```bash
source .venv/bin/activate
cp .env.example .env
```

### 3) Fill the Environment File

```ini
OPENROUTER_API_KEY="your-openrouter-api-key"
OPENROUTER_MODEL="google/gemini-2.5-flash-lite"
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
SPOTIFY_CLIENT_ID="your-spotify-client-id"
SPOTIFY_CLIENT_SECRET="your-spotify-client-secret"
SPOTIFY_REDIRECT_URI=""
SPOTIFY_DEFAULT_MARKET="ID"

# Required in production. Long random string (>=32 chars).
SESSION_SECRET=""
# Salt used to hash client IPs before persisting analytics.
IP_HASH_SALT=""

# Rate limits (slowapi syntax).
RATE_LIMIT_RECOMMEND="10/minute"
RATE_LIMIT_SUGGESTIONS="30/minute"

# Public base URL of this app (used for OpenRouter HTTP-Referer).
APP_PUBLIC_URL="http://localhost:8000"
# Set to true behind HTTPS in production.
COOKIE_SECURE="false"
```

You can switch the LLM model at runtime via `OPENROUTER_MODEL` (for example `openai/gpt-4o-mini`, `anthropic/claude-3.5-sonnet`, or any model available in your OpenRouter account).

For production deployments (for example Vercel), set `SPOTIFY_REDIRECT_URI` explicitly to the exact callback URL registered in Spotify Dashboard, such as:

```text
https://smart-discover.vercel.app/callback
```

Important: Spotify requires an exact match (scheme, domain, and path).

### Environment variables reference

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `OPENROUTER_API_KEY` | yes (LLM mode) | - | OpenRouter API key. If empty, app runs in heuristic-only fallback. |
| `OPENROUTER_MODEL` | no | `google/gemini-2.5-flash-lite` | LLM model id. |
| `OPENROUTER_BASE_URL` | no | `https://openrouter.ai/api/v1` | OpenRouter base URL. |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | yes (real catalog) | - | Spotify Web API credentials. If empty, app uses mock candidates. |
| `SPOTIFY_REDIRECT_URI` | prod | derived | Exact callback URL registered in Spotify Dashboard. |
| `SPOTIFY_DEFAULT_MARKET` | no | `ID` | Spotify market code fallback. Auto-derived from intent locale when possible. |
| `SESSION_SECRET` | **prod** | dev placeholder | Signs the HttpOnly OAuth session cookie. Use a long random string in production. |
| `IP_HASH_SALT` | prod | dev placeholder | Salt used to SHA256-hash client IPs before storing analytics. |
| `RATE_LIMIT_RECOMMEND` | no | `10/minute` | slowapi limit on `/recommend`. |
| `RATE_LIMIT_SUGGESTIONS` | no | `30/minute` | slowapi limit on `/api/prompt-suggestions`. |
| `APP_PUBLIC_URL` | no | `http://localhost:8000` | Public base URL; used as `HTTP-Referer` for OpenRouter. |
| `COOKIE_SECURE` | prod | `false` | Set `true` when serving behind HTTPS. |
| `SUPABASE_URL` / `SUPABASE_API_KEY` | no | - | Optional analytics destination for prompt logs. |
| `AGENT_LOOP_ENABLED` | no | `false` | Enable orchestrator tool-use loop by default. Individual requests can still force it with `agentic_mode="agentic"` when the LLM is enabled. |
| `AGENT_LOOP_MAX_ITERATIONS` | no | `3` | Hard limit for orchestrator iterations. |
| `AGENT_LOOP_TIMEOUT_S` | no | `30.0` | Wall-clock budget for the orchestrator. |
| `GENIUS_ACCESS_TOKEN` | no | - | Genius API bearer token for optional lyric-signal enrichment. |
| `GENIUS_LYRICS_ENABLED` | no | `false` | Enables bounded Genius lookup for top candidates only. |
| `GENIUS_LYRICS_TOP_N` | no | `10` | Maximum candidates enriched per request to avoid token/API explosion. |
| `GENIUS_LYRICS_CACHE_TTL_S` | no | `86400` | TTL for cached Genius lyric signals. |
| `EVAL_PASS_THRESHOLD` | no | `0.7` | Pass threshold used by `evals/run_eval.py` exit code. |

Note: the official Genius API does not return full lyric text. SmartDiscover derives bounded semantic signals only from Genius description metadata; title-only matches receive no inferred themes or sentiment. The system does not claim to know full lyric meaning. Full lyric-text retrieval should use a licensed lyrics provider before storing or displaying lyrics.

### Privacy disclosure

When Supabase is configured, each `/recommend` request persists:

- The prompt text and target count.
- A SHA256 hash of the client IP (salted with `IP_HASH_SALT`, **not reversible**).
- The User-Agent header.

No Spotify account data is ever stored. The Spotify access token lives only in an HttpOnly, signed session cookie scoped to your browser; it never reaches `localStorage` or analytics.

### 4) Run the Application

```powershell
uvicorn app.main:app --reload
```

Open the app at http://127.0.0.1:8000/

### Agentic demo mode

Use the **Agent Mode** selector in the form:

- `Auto`: follows `AGENT_LOOP_ENABLED`.
- `Agentic`: forces the orchestrator loop when `OPENROUTER_API_KEY` is configured.
- `Linear`: bypasses the orchestrator for a deterministic pipeline baseline.

The **Behind the scenes** panel shows the effective mode, loop status, tool path, trace summaries, and fallback reason.

## Demo

<div align="center">
  <img src="assets/demo/demo-1.gif" alt="SmartDiscover Demo 1" width="100%" />
  <br /><br />
  <img src="assets/demo/demo-1.2.gif" alt="SmartDiscover Demo 1.2" width="100%" />
</div>

---

## Example User Prompts

- "Late-night coding tracks that keep me focused but not sleepy"
- "A bright and upbeat vibe for an afternoon road trip"
- "Relaxing background music for reading, preferably instrumental"

## Create Spotify Playlists

After generating recommendations, you can save them directly to your Spotify account.

### User Flow

1. **Connect Spotify**: Click the **Connect Spotify** button in the sidebar and sign in to Spotify.
2. **Authorize Access**: Approve playlist permissions when prompted.
3. **Generate Recommendations**: Run your prompt as usual.
4. **Save as Spotify Playlist**: Click **Save as Spotify Playlist** to create a playlist from the selected tracks.

### Required OAuth Scopes

SmartDiscover requests the following Spotify scopes:

- `playlist-modify-public`
- `playlist-modify-private`

### Privacy Behavior

Playlists created by SmartDiscover are **private by default**.
You can change playlist visibility later from your Spotify account.

## Audio Preview Behavior

SmartDiscover includes a mini preview player in each recommendation card.

- If Spotify provides `preview_url`, the card shows an active **Play/Pause** preview control.
- If `preview_url` is missing, SmartDiscover applies a backend fallback by checking Spotify Embed metadata (`__NEXT_DATA__`) to recover `audioPreview.url` when available.
- If no preview is found after fallback, the card still shows a disabled **No Preview** state so users can see that preview is unavailable for that track.

Notes:

- Preview availability is controlled by Spotify catalog metadata and may vary by region/licensing.
- Fallback is best-effort and bounded per request to keep latency stable.

## Fallback Mode

If Spotify credentials are missing or invalid, the application still runs in fallback mode so the interface can be demonstrated.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET`  | `/health` | Liveness check. |
| `GET`  | `/spotify/health` | Spotify reachability. |
| `GET`  | `/llm/health` | OpenRouter reachability. |
| `POST` | `/recommend` | Run the full pipeline. Body: `{text, target_count?, agentic_mode?}` where `agentic_mode` is `auto`, `agentic`, or `linear`. |
| `POST` | `/refine` | Multi-turn refine. Body: `{previous_profile, previous_track_ids, refinement_text, target_count?, agentic_mode?}`. |
| `GET`  | `/api/prompt-suggestions?q=` | Recent-prompt autocomplete (rate-limited). |
| `GET`  | `/auth/login` → `/auth/callback` | Spotify OAuth (HttpOnly cookie session, CSRF-protected). |
| `GET`  | `/auth/status` | Returns `{connected, expires_at}`. |
| `POST` | `/auth/logout` | Clears the session cookie. |
| `POST` | `/create-playlist` | Saves the current selection as a Spotify playlist (requires session cookie). |

## Eval harness

Offline regression for the Profiler agent.

```powershell
.\.venv\Scripts\Activate.ps1
python -m evals.run_eval
```

Outputs aggregate intent metrics plus `meaning_required_match`, `lyrical_intent_recall`, and `semantic_overall`, then saves a per-prompt JSON to `evals/results/`. Exits `0` only when both `overall` and `semantic_overall` meet `EVAL_PASS_THRESHOLD`. Edit `evals/golden_prompts.json` to update the gold set.

## Tech Stack

- Backend: FastAPI
- Language: Python
- LLM runtime: OpenRouter
- Music source: Spotify Web API
- Frontend: HTML, CSS, JavaScript

## License

This project is distributed under the MIT License. See LICENSE for details.

## Legal Disclaimer

- This application uses third-party APIs (Spotify and external LLM providers).
- This project is independent and is not affiliated with, endorsed by, or sponsored by Spotify.
- All Spotify trademarks, logos, and brand assets belong to Spotify AB.
- API key usage must comply with each provider's Terms of Service.

---

<div align="center">
  <strong>Maintainer</strong><br />
  wahyu muliadi siregar<br />
  Copyright (c) 2026
</div>
