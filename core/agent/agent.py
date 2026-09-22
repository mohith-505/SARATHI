"""SARATHI V0.1 Core Brain.

Responsibilities:
- Hold conversation state (system prompt + history).
- Invoke the configured AI provider.
- Enforce a bounded history window.
- Never fabricate a response: if the provider fails, the user message is
  rolled back and the exception propagates.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from core.config.settings import SarathiSettings
from core.logging.logger import get_logger
from core.prompts.system import SARATHI_SYSTEM_PROMPT
from core.types.messages import Conversation, Role
from models.base import AIProvider

log = get_logger("agent")


class Agent:
    def __init__(self, provider: AIProvider, settings: SarathiSettings) -> None:
        self.provider = provider
        self.settings = settings
        self.conversation = Conversation()
        self._seed_system_prompt()

    def _seed_system_prompt(self) -> None:
        self.conversation.add_system(SARATHI_SYSTEM_PROMPT)

    def _trim_history(self) -> None:
        """Keep system prompt + the most recent N-1 messages."""
        max_messages = self.settings.agent.max_history_messages
        messages = self.conversation.messages
        if len(messages) <= max_messages:
            return
        system = messages[0]
        if system.role is not Role.SYSTEM:
            # Defensive: if somehow the system prompt isn't first, rebuild.
            log.warning("System prompt was not at index 0; rebuilding.")
            self.conversation.messages = messages[-(max_messages):]
            return
        tail = messages[-(max_messages - 1):]
        self.conversation.messages = [system, *tail]

    async def ask(self, user_input: str) -> str:
        """Single-shot request; returns the full assistant response."""
        self.conversation.add_user(user_input)
        self._trim_history()
        log.debug("chat() with %d messages", len(self.conversation.messages))
        try:
            reply = await self.provider.chat(
                self.conversation.messages, model=self.settings.model.name
            )
        except Exception:
            # Roll back the user turn so the conversation isn't left dangling.
            self.conversation.messages.pop()
            raise
        self.conversation.add_assistant(reply)
        return reply

    async def stream(self, user_input: str) -> AsyncIterator[str]:
        """Streamed request; yields chunks, commits assistant turn on success."""
        self.conversation.add_user(user_input)
        self._trim_history()
        log.debug("stream() with %d messages", len(self.conversation.messages))

        buffer: list[str] = []
        try:
            async for chunk in self.provider.stream(
                self.conversation.messages, model=self.settings.model.name
            ):
                buffer.append(chunk)
                yield chunk
        except Exception:
            self.conversation.messages.pop()
            raise

        self.conversation.add_assistant("".join(buffer))

    def reset(self) -> None:
        """Clear conversation history but keep the system prompt."""
        self.conversation.clear()
        self._seed_system_prompt()
