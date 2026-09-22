from __future__ import annotations

from core.types.messages import Conversation, Message, Role


def test_message_to_dict_minimal():
    m = Message(role=Role.USER, content="hello")
    assert m.to_dict() == {"role": "user", "content": "hello"}


def test_message_to_dict_includes_name_when_set():
    m = Message(role=Role.TOOL, content="x", name="system_info")
    d = m.to_dict()
    assert d["name"] == "system_info"


def test_conversation_helpers():
    c = Conversation()
    c.add_system("sys")
    c.add_user("hi")
    c.add_assistant("hello")
    assert len(c) == 3
    assert [m.role for m in c.messages] == [Role.SYSTEM, Role.USER, Role.ASSISTANT]
    assert c.to_payload()[0] == {"role": "system", "content": "sys"}


def test_conversation_clear():
    c = Conversation()
    c.add_user("hi")
    c.clear()
    assert len(c) == 0
