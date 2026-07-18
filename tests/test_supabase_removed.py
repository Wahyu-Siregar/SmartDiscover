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
