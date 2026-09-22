from __future__ import annotations

from pathlib import Path

import pytest

from core.agent.agent import Agent
from core.config.settings import SarathiSettings
from core.types.messages import Role


@pytest.fixture
def settings() -> SarathiSettings:
    return SarathiSettings.load(Path("does-not-exist.toml"))


@pytest.mark.asyncio
async def test_ask_appends_user_and_assistant(fake_provider, settings):
    fake_provider.response = "hello world"
    agent = Agent(fake_provider, settings)

    reply = await agent.ask("hi")
    assert reply == "hello world"

    roles = [m.role for m in agent.conversation.messages]
    assert roles[0] is Role.SYSTEM
    assert roles[-2] is Role.USER
    assert roles[-1] is Role.ASSISTANT


@pytest.mark.asyncio
async def test_stream_appends_after_completion(fake_provider, settings):
    fake_provider.response = "one two three"
    agent = Agent(fake_provider, settings)

    chunks: list[str] = []
    async for c in agent.stream("go"):
        chunks.append(c)

    assert "".join(chunks).strip() == "one two three"
    assert agent.conversation.messages[-1].role is Role.ASSISTANT
    assert agent.conversation.messages[-1].content.strip() == "one two three"


@pytest.mark.asyncio
async def test_failed_chat_rolls_back_user_message(fake_provider, settings):
    fake_provider.fail_chat = True
    agent = Agent(fake_provider, settings)

    before = len(agent.conversation)
    with pytest.raises(RuntimeError):
        await agent.ask("boom")
    assert len(agent.conversation) == before


@pytest.mark.asyncio
async def test_history_is_trimmed(fake_provider, settings):
    settings.agent.max_history_messages = 4
    agent = Agent(fake_provider, settings)
    for i in range(10):
        await agent.ask(f"msg {i}")
    # system + at most 3 others
    assert len(agent.conversation.messages) <= 4
    assert agent.conversation.messages[0].role is Role.SYSTEM


def test_reset_keeps_system_prompt(fake_provider, settings):
    agent = Agent(fake_provider, settings)
    agent.conversation.add_user("x")
    agent.reset()
    assert len(agent.conversation.messages) == 1
    assert agent.conversation.messages[0].role is Role.SYSTEM
