from sarathi.core.conversation import Conversation
from sarathi.core.types import Role


def test_conversation_keeps_system_prompt_and_recent_messages() -> None:
    conversation = Conversation("system", max_messages=2)
    conversation.add_user("first")
    conversation.add_assistant("first reply")
    conversation.add_user("second")

    messages = conversation.messages_for_model()
    assert [message.role for message in messages] == [Role.SYSTEM, Role.ASSISTANT, Role.USER]
    assert [message.content for message in messages] == ["system", "first reply", "second"]


def test_conversation_clear_removes_only_short_term_context() -> None:
    conversation = Conversation("system")
    conversation.add_user("hello")
    conversation.clear()

    assert [message.content for message in conversation.messages_for_model()] == ["system"]
