"""Conversation and message primitives used across SARATHI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(slots=True)
class Message:
    """A single message in a conversation."""

    role: Role
    content: str
    name: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Minimal wire-format representation for LLM providers."""
        payload: dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.name is not None:
            payload["name"] = self.name
        return payload


@dataclass(slots=True)
class Conversation:
    """Ordered message history with helpers."""

    messages: list[Message] = field(default_factory=list)

    def add(self, message: Message) -> None:
        self.messages.append(message)

    def add_system(self, content: str) -> Message:
        msg = Message(role=Role.SYSTEM, content=content)
        self.add(msg)
        return msg

    def add_user(self, content: str) -> Message:
        msg = Message(role=Role.USER, content=content)
        self.add(msg)
        return msg

    def add_assistant(self, content: str) -> Message:
        msg = Message(role=Role.ASSISTANT, content=content)
        self.add(msg)
        return msg

    def to_payload(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self.messages]

    def clear(self) -> None:
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)
