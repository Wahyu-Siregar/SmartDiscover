"""SmartDiscover offline eval harness.

Runs the Profiler against a curated golden prompt set and reports
mood/genre/locale accuracy. Designed to be the regression gate for
prompt + model changes.

Usage:
    .\\.venv\\Scripts\\Activate.ps1
    python -m evals.run_eval

Set OPENROUTER_API_KEY in .env to evaluate the LLM path; otherwise
only the heuristic path is exercised.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.services.openrouter_client import OpenRouterClient
from app.services.profiler import ProfilerAgent


GOLDEN_PATH = Path(__file__).with_name("golden_prompts.json")
RESULTS_DIR = Path(__file__).with_name("results")


def _load_golden() -> list[dict[str, Any]]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _genre_recall(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 1.0
    sa = set(actual or [])
    return sum(1 for g in expected if g in sa) / len(expected)


async def _run() -> int:
    golden = _load_golden()

    async with httpx.AsyncClient(timeout=60.0) as client:
        llm = OpenRouterClient(client)
        agent = ProfilerAgent(llm)

        rows: list[dict[str, Any]] = []
        started = time.perf_counter()

        for entry in golden:
            prompt = entry["prompt"]
            try:
                profile = await agent.profile(prompt)
            except Exception as exc:  # noqa: BLE001
                rows.append({"prompt": prompt, "error": str(exc)})
                continue

            mood_match = profile.mood == entry["expected_mood"]
            genre_recall = _genre_recall(entry["expected_genre"], profile.genre)
            genre_jaccard = _jaccard(entry["expected_genre"], profile.genre)
            locale_match = profile.locale == entry["expected_locale"]
            strict_match = bool(profile.strict_locale) == bool(entry["expected_strict_locale"])

            rows.append(
                {
                    "prompt": prompt,
                    "expected": {
                        "mood": entry["expected_mood"],
                        "genre": entry["expected_genre"],
                        "locale": entry["expected_locale"],
                        "strict_locale": entry["expected_strict_locale"],
                    },
                    "actual": profile.model_dump(),
                    "scores": {
                        "mood_match": int(mood_match),
                        "genre_recall": round(genre_recall, 3),
                        "genre_jaccard": round(genre_jaccard, 3),
                        "locale_match": int(locale_match),
                        "strict_match": int(strict_match),
                    },
                    "used_llm": agent.last_used_llm,
                }
            )

        elapsed_s = time.perf_counter() - started

    valid = [r for r in rows if "error" not in r]
    if not valid:
        print("No valid rows; aborting.", file=sys.stderr)
        return 1

    agg = {
        "mood_match": sum(r["scores"]["mood_match"] for r in valid) / len(valid),
        "genre_recall": sum(r["scores"]["genre_recall"] for r in valid) / len(valid),
        "genre_jaccard": sum(r["scores"]["genre_jaccard"] for r in valid) / len(valid),
        "locale_match": sum(r["scores"]["locale_match"] for r in valid) / len(valid),
        "strict_match": sum(r["scores"]["strict_match"] for r in valid) / len(valid),
    }
    overall = (agg["mood_match"] + agg["genre_recall"] + agg["locale_match"] + agg["strict_match"]) / 4
    threshold = settings.eval_pass_threshold

    print("=" * 60)
    print(f"SmartDiscover eval: {len(valid)}/{len(rows)} prompts ({elapsed_s:.1f}s)")
    print(f"  LLM enabled         : {llm.enabled}")
    print(f"  mood_match          : {agg['mood_match']:.3f}")
    print(f"  genre_recall        : {agg['genre_recall']:.3f}")
    print(f"  genre_jaccard       : {agg['genre_jaccard']:.3f}")
    print(f"  locale_match        : {agg['locale_match']:.3f}")
    print(f"  strict_locale_match : {agg['strict_match']:.3f}")
    print(f"  overall             : {overall:.3f}  (threshold {threshold:.2f})")
    print("=" * 60)

    failures = [r for r in valid if r["scores"]["mood_match"] == 0 or r["scores"]["genre_recall"] < 0.5]
    if failures:
        print(f"\n{len(failures)} weak rows (showing up to 8):")
        for r in failures[:8]:
            print(
                f"  - {r['prompt']!r:60s} mood={r['actual']['mood']:>10s} "
                f"genre={r['actual']['genre']} expected_genre={r['expected']['genre']}"
            )

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"{int(time.time())}.json"
    out_path.write_text(
        json.dumps(
            {"aggregate": agg, "overall": overall, "threshold": threshold, "rows": rows},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nResults saved to {out_path}")

    return 0 if overall >= threshold else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
