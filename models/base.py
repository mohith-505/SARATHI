"""Abstract AI provider interface.

Every concrete provider (Ollama, OpenAI, Gemini, ...) implements this ABC.
The agent core must never import a concrete provider directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from core.types.messages import Message


class AIProvider(ABC):
    """Provider contract used by the agent core."""

    name: str = "base"

    @abstractmethod
    async def chat(
        self, messages: list[Message], *, model: str | None = None
    ) -> str:
        """Return a single non-streamed assistant response."""

    @abstractmethod
    def stream(
        self, messages: list[Message], *, model: str | None = None
    ) -> AsyncIterator[str]:
        """Return an async iterator yielding text chunks."""

    async def health(self) -> bool:
        """Return True if the provider is reachable. Default: True."""
        return True

    async def close(self) -> None:
        """Release resources. Default: no-op."""
        return None
