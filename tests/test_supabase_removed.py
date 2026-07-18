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
