import json
import re
from typing import Any

import httpx
from tenacity import AsyncRetrying, RetryError, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.config import settings


_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class _RetryableHTTPError(Exception):
    """Internal marker so tenacity retries 429/5xx without retrying 4xx."""


def _summarize(result: Any, max_len: int = 240) -> str:
    """Compact, log-friendly representation of a tool result."""
    try:
        if isinstance(result, dict):
            keys = list(result.keys())[:6]
            return f"dict(keys={keys}, len={len(result)})"
        if isinstance(result, list):
            return f"list(len={len(result)})"
        text = str(result)
        return text if len(text) <= max_len else text[: max_len - 3] + "..."
    except Exception:
        return "<unrepr>"


def _summarize_tool_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if "query" in arguments:
        summary["query_chars"] = len(str(arguments.get("query") or ""))
    if "count" in arguments:
        summary["count"] = arguments.get("count")
    if "track_ids" in arguments:
        raw_ids = arguments.get("track_ids")
        summary["track_ids_count"] = len(raw_ids) if isinstance(raw_ids, list) else 0
    for key in ("min_energy", "max_energy", "min_valence", "max_valence", "min_tempo", "max_tempo"):
        if key in arguments:
            summary[key] = arguments[key]
    return summary


class OpenRouterClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self.model = settings.openrouter_model
        self.api_key = settings.openrouter_api_key
        self._client = client

    def attach_client(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def _post_chat(self, payload: dict[str, Any], timeout: float) -> httpx.Response:
        assert self._client is not None, "OpenRouterClient.attach_client() must be called before use"
        resp = await self._client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=timeout,
        )
        if resp.status_code in _RETRYABLE_STATUSES:
            raise _RetryableHTTPError(f"OpenRouter status {resp.status_code}")
        return resp

    async def _post_chat_with_retry(self, payload: dict[str, Any], timeout: float) -> httpx.Response | None:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential_jitter(initial=0.4, max=2.0),
                retry=retry_if_exception_type((_RetryableHTTPError, httpx.TransportError, httpx.TimeoutException)),
                reraise=False,
            ):
                with attempt:
                    return await self._post_chat(payload, timeout)
        except RetryError:
            return None
        except Exception:
            return None
        return None

    async def health_check(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                "status": "disabled",
                "ok": False,
                "details": "OPENROUTER_API_KEY belum diisi.",
            }

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Reply with the word ok."},
                    {"role": "user", "content": "health check"},
                ],
                "max_tokens": 8,
                "temperature": 0,
            }
            resp = await self._post_chat_with_retry(payload, timeout=30.0)
            if resp is None or resp.status_code != 200:
                code = resp.status_code if resp is not None else "n/a"
                return {
                    "status": "openrouter-error",
                    "ok": False,
                    "details": f"OpenRouter returned {code}",
                }
            return {
                "status": "ok",
                "ok": True,
                "details": "OpenRouter reachable.",
            }
        except Exception as exc:
            return {
                "status": "openrouter-exception",
                "ok": False,
                "details": str(exc),
            }

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 700,
        *,
        temperature: float = 0.2,
        json_mode: bool = True,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        resp = await self._post_chat_with_retry(payload, timeout=45.0)
        if resp is None or resp.status_code != 200:
            return None

        try:
            body = resp.json()
            content = (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return self._parse_json_content(content)
        except Exception:
            return None

    async def chat_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_executor,  # async (name: str, arguments: dict) -> Any
        *,
        max_iterations: int = 3,
        max_tokens: int = 1000,
        temperature: float = 0.2,
    ) -> dict[str, Any] | None:
        """Tool-calling loop. `tool_executor` runs each tool call and returns a JSON-serializable result.

        Returns the final assistant message dict plus a `trace` of tool calls, or None on failure.
        """
        if not self.enabled:
            return None

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        trace: list[dict[str, Any]] = []

        for iteration in range(max_iterations):
            payload = {
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            resp = await self._post_chat_with_retry(payload, timeout=60.0)
            if resp is None or resp.status_code != 200:
                return None

            try:
                body = resp.json()
                msg = body.get("choices", [{}])[0].get("message", {}) or {}
            except Exception:
                return None

            tool_calls = msg.get("tool_calls") or []
            # Append assistant message (must include tool_calls if any).
            assistant_entry: dict[str, Any] = {"role": "assistant", "content": msg.get("content") or ""}
            if tool_calls:
                assistant_entry["tool_calls"] = tool_calls
            messages.append(assistant_entry)

            if not tool_calls:
                # Model decided to stop or no tools requested.
                return {"message": msg, "trace": trace, "iterations": iteration + 1}

            # Execute tools and append tool results.
            import json as _json
            for call in tool_calls:
                fn = call.get("function", {}) or {}
                name = fn.get("name", "")
                args_raw = fn.get("arguments", "{}") or "{}"
                try:
                    arguments = _json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
                except Exception:
                    arguments = {}
                try:
                    result = await tool_executor(name, arguments)
                except Exception as exc:
                    result = {"error": str(exc)}
                trace.append({
                    "name": name,
                    "arguments_summary": _summarize_tool_arguments(arguments),
                    "result_summary": _summarize(result),
                })
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id", ""),
                        "name": name,
                        "content": _json.dumps(result, default=str)[:4000],
                    }
                )

        # Iteration cap reached.
        return {"message": messages[-1] if messages else {}, "trace": trace, "iterations": max_iterations}

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.app_public_url,
            "X-Title": "SmartDiscover",
        }

    def _parse_json_content(self, content: str) -> dict[str, Any] | None:
        text = content.strip()
        if not text:
            return None

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if fenced:
            try:
                parsed = json.loads(fenced.group(1))
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None

        # Last attempt: first JSON object substring.
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
        return None
