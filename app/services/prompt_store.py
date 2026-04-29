from __future__ import annotations

import hashlib
import logging
from urllib.parse import quote

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


def hash_client_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    salt = settings.ip_hash_salt or ""
    digest = hashlib.sha256(f"{salt}|{ip}".encode("utf-8")).hexdigest()
    # Truncate to 32 hex chars (128 bits) — plenty for analytics dedupe.
    return digest[:32]


class PromptStore:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._url = settings.supabase_url.rstrip("/")
        self._api_key = settings.supabase_api_key.strip()
        self._table = settings.supabase_prompt_table.strip() or "prompt_logs"
        self._client = client

    def attach_client(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return bool(self._url and self._api_key)

    def _headers(self, *, content_type: bool = False, prefer_minimal: bool = False) -> dict[str, str]:
        headers = {
            "apikey": self._api_key,
            "Authorization": f"Bearer {self._api_key}",
        }
        if content_type:
            headers["Content-Type"] = "application/json"
        if prefer_minimal:
            headers["Prefer"] = "return=minimal"
        return headers

    async def save_prompt(
        self,
        *,
        prompt_text: str,
        target_count: int | None,
        source: str,
        client_ip: str | None,
        user_agent: str | None,
    ) -> bool:
        if not self.enabled or self._client is None:
            return False

        endpoint = f"{self._url}/rest/v1/{self._table}"
        payload = {
            "prompt_text": prompt_text,
            "target_count": target_count,
            "source": source,
            "client_ip": hash_client_ip(client_ip),
            "user_agent": user_agent,
        }

        try:
            response = await self._client.post(
                endpoint,
                json=payload,
                headers=self._headers(content_type=True, prefer_minimal=True),
                timeout=8.0,
            )
            response.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Failed to persist prompt to Supabase: %s", exc)
            return False

    async def search_suggestions(self, q: str, *, limit: int = 15) -> list[str]:
        if not self.enabled or self._client is None:
            return []

        endpoint = (
            f"{self._url}/rest/v1/{self._table}"
            f"?select=prompt_text&order=created_at.desc&limit={max(1, min(50, limit))}"
        )
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            endpoint += f"&prompt_text=ilike.{quote(pattern)}"

        try:
            response = await self._client.get(endpoint, headers=self._headers(), timeout=5.0)
            if response.status_code != 200:
                return []
            data = response.json()
        except Exception as exc:
            logger.warning("Failed to fetch prompt suggestions: %s", exc)
            return []

        seen: set[str] = set()
        suggestions: list[str] = []
        for row in data:
            prompt = (row.get("prompt_text") or "").strip()
            if prompt and prompt not in seen:
                suggestions.append(prompt)
                seen.add(prompt)
        return suggestions[:limit]
