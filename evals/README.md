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
- Process exit code: 0 if both `overall` and `semantic_overall` meet `EVAL_PASS_THRESHOLD` (default 0.7), else 1.

## Metrics

- `mood_match` — exact match on canonical mood label.
- `genre_recall` — fraction of expected genres present in actual.
- `genre_jaccard` — IoU of expected vs actual genre sets.
- `locale_match` — exact match on locale.
- `strict_locale_match` — boolean equality.
- `overall` — mean of `mood_match`, `genre_recall`, `locale_match`, `strict_match`.
- `meaning_required_match` — whether lyric-sensitive intent was detected correctly.
- `lyrical_intent_recall` — fraction of expected meaning terms preserved in `lyrical_intent`.
- `semantic_overall` — mean of the two lyric-intent metrics on semantic rows.

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

For lyric-sensitive rows, also add `expected_meaning_required` and
`expected_lyrical_terms`. These grade intent preservation, not a claim that
SmartDiscover has read the full lyrics.

Keep prompts diverse (mood-only, genre-only, activity, locale, lyric intent, mixed).
Aim for ~40–80 entries.
