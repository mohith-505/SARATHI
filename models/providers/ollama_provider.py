"""Ollama provider (local models).

Uses the /api/chat endpoint:
    POST {base_url}/api/chat
with stream=False for chat() and stream=True for stream().
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from core.errors.exceptions import (
    ModelResponseError,
    ModelUnavailableError,
    ProviderConnectionError,
)
from core.logging.logger import get_logger
from core.types.messages import Message
from models.base import AIProvider

log = get_logger("models.ollama")


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.1:8b",
        temperature: float = 0.2,
        request_timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.temperature = temperature
        self.request_timeout = request_timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(request_timeout, connect=5.0),
            headers={"Content-Type": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            r = await self._client.get("/api/tags", timeout=5.0)
            return r.status_code == 200
        except httpx.HTTPError as e:
            log.debug("Ollama health check failed: %s", e)
            return False

    def _payload(
        self, messages: list[Message], model: str, stream: bool
    ) -> dict[str, object]:
        return {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": stream,
            "options": {"temperature": self.temperature},
        }

    async def chat(
        self, messages: list[Message], *, model: str | None = None
    ) -> str:
        model_name = model or self.default_model
        payload = self._payload(messages, model_name, stream=False)
        try:
            r = await self._client.post("/api/chat", json=payload)
        except httpx.ConnectError as e:
            raise ProviderConnectionError(
                f"Cannot reach Ollama at {self.base_url}. Is `ollama serve` running?"
            ) from e
        except httpx.HTTPError as e:
            raise ModelUnavailableError(f"Ollama request failed: {e}") from e

        if r.status_code == 404:
            raise ModelUnavailableError(
                f"Model '{model_name}' not found in Ollama. Try: ollama pull {model_name}"
            )
        if r.status_code >= 400:
            raise ModelResponseError(
                f"Ollama returned HTTP {r.status_code}: {r.text[:200]}"
            )

        try:
            data = r.json()
        except ValueError as e:
            raise ModelResponseError(
                f"Ollama returned non-JSON response: {r.text[:200]}"
            ) from e

        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as e:
            raise ModelResponseError(
                f"Malformed Ollama chat response: {json.dumps(data)[:200]}"
            ) from e

    async def stream(
        self, messages: list[Message], *, model: str | None = None
    ) -> AsyncIterator[str]:
        model_name = model or self.default_model
        payload = self._payload(messages, model_name, stream=True)
        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as r:
                if r.status_code == 404:
                    raise ModelUnavailableError(
                        f"Model '{model_name}' not found in Ollama. "
                        f"Try: ollama pull {model_name}"
                    )
                if r.status_code >= 400:
                    body = await r.aread()
                    raise ModelResponseError(
                        f"Ollama stream HTTP {r.status_code}: {body[:200]!r}"
                    )
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        log.debug("Skipping non-JSON stream line: %r", line[:80])
                        continue
                    if chunk.get("done"):
                        break
                    content = (chunk.get("message") or {}).get("content")
                    if content:
                        yield content
        except httpx.ConnectError as e:
            raise ProviderConnectionError(
                f"Cannot reach Ollama at {self.base_url}. Is `ollama serve` running?"
            ) from e
        except httpx.HTTPError as e:
            raise ModelUnavailableError(f"Ollama stream failed: {e}") from e
