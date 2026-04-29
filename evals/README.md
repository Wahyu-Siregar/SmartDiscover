# SmartDiscover Eval Harness

Standalone offline eval for the **Profiler** agent. Tracks regression
when prompts, model, or heuristic logic change.

## Run

```powershell
.\.venv\Scripts\Activate.ps1
python -m evals.run_eval
```

If `OPENROUTER_API_KEY` is set in `.env`, the LLM path (hybrid) is
exercised; otherwise only the heuristic fallback is graded.

## Output

- Console: aggregate metrics + weak rows.
- `evals/results/<timestamp>.json`: full per-prompt breakdown.
- Process exit code: 0 if `overall >= EVAL_PASS_THRESHOLD` (default 0.7), else 1.

## Metrics

- `mood_match` — exact match on canonical mood label.
- `genre_recall` — fraction of expected genres present in actual.
- `genre_jaccard` — IoU of expected vs actual genre sets.
- `locale_match` — exact match on locale.
- `strict_locale_match` — boolean equality.
- `overall` — mean of `mood_match`, `genre_recall`, `locale_match`, `strict_match`.

## Updating the golden set

Edit `evals/golden_prompts.json`. Each entry:

```json
{
  "prompt": "lagu batak buat malam minggu",
  "expected_mood": "neutral",
  "expected_genre": ["batak"],
  "expected_locale": "",
  "expected_strict_locale": false
}
```

Keep prompts diverse (mood-only, genre-only, activity, locale, mixed).
Aim for ~40–80 entries.
