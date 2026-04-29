"""Validate hashed-IP behavior and search_suggestions encapsulation."""
from __future__ import annotations

import asyncio

import pytest

from app.services.prompt_store import PromptStore, hash_client_ip


def test_hash_client_ip_is_deterministic_and_truncated(monkeypatch) -> None:
    monkeypatch.setattr("app.services.prompt_store.settings.ip_hash_salt", "salt-A")
    a = hash_client_ip("203.0.113.42")
    b = hash_client_ip("203.0.113.42")
    c = hash_client_ip("203.0.113.43")
    assert a == b
    assert a != c
    assert len(a) == 32
    assert hash_client_ip(None) is None
    assert hash_client_ip("") is None


def test_hash_client_ip_changes_with_salt(monkeypatch) -> None:
    monkeypatch.setattr("app.services.prompt_store.settings.ip_hash_salt", "salt-A")
    a = hash_client_ip("203.0.113.42")
    monkeypatch.setattr("app.services.prompt_store.settings.ip_hash_salt", "salt-B")
    b = hash_client_ip("203.0.113.42")
    assert a != b


class _FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")


class _FakeClient:
    def __init__(self) -> None:
        self.posted: list[dict] = []

    async def post(self, url, json, headers, timeout):
        self.posted.append({"url": url, "json": json, "headers": headers})
        return _FakeResponse(201)


def test_save_prompt_hashes_ip_before_persist(monkeypatch) -> None:
    monkeypatch.setattr("app.services.prompt_store.settings.supabase_url", "https://x.supabase.co")
    monkeypatch.setattr("app.services.prompt_store.settings.supabase_api_key", "anon-key")
    monkeypatch.setattr("app.services.prompt_store.settings.ip_hash_salt", "test-salt")

    store = PromptStore()
    fake_client = _FakeClient()
    store.attach_client(fake_client)  # type: ignore[arg-type]
    assert store.enabled

    ok = asyncio.run(
        store.save_prompt(
            prompt_text="lagu fokus",
            target_count=5,
            source="web",
            client_ip="198.51.100.7",
            user_agent="pytest",
        )
    )
    assert ok is True
    assert len(fake_client.posted) == 1
    payload = fake_client.posted[0]["json"]
    assert payload["prompt_text"] == "lagu fokus"
    assert payload["user_agent"] == "pytest"
    # Crucial: client_ip must NOT contain raw IP.
    assert "198.51.100.7" not in str(payload["client_ip"])
    assert payload["client_ip"] is not None
    assert len(payload["client_ip"]) == 32
