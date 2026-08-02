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


def test_prompt_history_ui_is_removed_but_static_quick_prompts_remain() -> None:
    sources = "\n".join(
        source.read_text(encoding="utf-8") for source in (ROOT / "frontend/src").rglob("*") if source.is_file()
    )

    for artifact in (
        "promptSuggestions",
        "bindPromptSuggestions",
        "prompt-suggestions",
        "prompt-suggestion",
        "prompt-suggestion-item",
        "textarea-wrapper",
        "ArrowDown",
        "ArrowUp",
    ):
        assert artifact not in sources

    composer = (ROOT / "frontend/src/components/PromptComposer.tsx").read_text(encoding="utf-8")
    assert "quickPrompts" in composer
    assert all(label in composer for label in ('t("chipFocus")', 't("chipRain")', 't("chipWorkout")'))
