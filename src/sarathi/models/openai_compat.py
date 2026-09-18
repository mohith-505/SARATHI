from __future__ import annotations
import json, uuid
from typing import Any
import httpx
from sarathi.core.types import Message, ModelResponse, ModelSpec, ToolCall, Usage


class OpenAICompatProvider:
    def __init__(self, base_url: str, api_key: str = "", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def complete(self, messages, spec, tools=None, temperature=0.7) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": spec.name,
            "messages": [m.to_api() for m in messages],
            "temperature": temperature,
        }
        if tools and spec.supports_tools:
            payload["tools"] = tools

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.base_url}/chat/completions",
                                  json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        choice = data["choices"][0]
        msg = choice.get("message", {})

        calls = []
        for tc in (msg.get("tool_calls") or []):
            fn = tc.get("function", {})
            raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                args = {"_malformed": raw}   # let the gateway reject it cleanly
            calls.append(ToolCall(id=tc.get("id") or str(uuid.uuid4()),
                                  name=fn.get("name", ""), args=args))

        u = data.get("usage") or {}
        usage = Usage(input_tokens=u.get("prompt_tokens", 0),
                      output_tokens=u.get("completion_tokens", 0))
        usage.cost_inr = spec.cost(usage)

        return ModelResponse(text=msg.get("content") or "", tool_calls=calls,
                             usage=usage, model=spec.name,
                             stop_reason=choice.get("finish_reason", ""))
