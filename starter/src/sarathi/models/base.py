"""Provider abstraction. The ONLY place that knows an API's wire format.

Everything above this layer speaks Message/ModelResponse. That is what lets you
swap Ollama for a cloud API for a future provider without touching agent code.
"""
from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
from sarathi.core.types import Message, ModelResponse, ModelSpec


@runtime_checkable
class ModelProvider(Protocol):
    async def complete(
        self,
        messages: list[Message],
        spec: ModelSpec,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> ModelResponse: ...
