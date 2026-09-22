from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from core.types.messages import Message
from models.base import AIProvider


class FakeProvider(AIProvider):
    """Deterministic in-memory provider for unit tests."""

    name = "fake"

    def __init__(self, response: str = "ok") -> None:
        self.response = response
        self.chat_calls: list[list[Message]] = []
        self.stream_calls: list[list[Message]] = []
        self.fail_chat = False
        self.fail_stream = False

    async def chat(self, messages, *, model=None):  # type: ignore[override]
        self.chat_calls.append(list(messages))
        if self.fail_chat:
            raise RuntimeError("fake chat failure")
        return self.response

    async def stream(self, messages, *, model=None) -> AsyncIterator[str]:  # type: ignore[override]
        self.stream_calls.append(list(messages))
        if self.fail_stream:
            raise RuntimeError("fake stream failure")
        for token in self.response.split():
            yield token + " "


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()
