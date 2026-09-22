"""Bounded in-memory conversation state for SARATHI V0.1."""
from __future__ import annotations

from dataclasses import dataclass, field

from sarathi.core.types import Message, Role


@dataclass
class Conversation:
    """Keeps recent dialogue while retaining the system identity every turn."""

    system_prompt: str
    max_messages: int = 12
    _messages: list[Message] = field(default_factory=list)

    def add_user(self, content: str) -> None:
        self._messages.append(Message(role=Role.USER, content=content))
        self._trim()

    def add_assistant(self, content: str) -> None:
        self._messages.append(Message(role=Role.ASSISTANT, content=content))
        self._trim()

    def messages_for_model(self) -> list[Message]:
        return [Message(role=Role.SYSTEM, content=self.system_prompt), *self._messages]

    def clear(self) -> None:
        self._messages.clear()

    def _trim(self) -> None:
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages :]
