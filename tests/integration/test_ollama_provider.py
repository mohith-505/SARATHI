from __future__ import annotations

import httpx
import pytest
import respx

from core.errors.exceptions import (
    ModelResponseError,
    ModelUnavailableError,
    ProviderConnectionError,
)
from core.types.messages import Message, Role
from models.providers.ollama_provider import OllamaProvider

BASE = "http://localhost:11434"


def _user(content: str = "hi") -> Message:
    return Message(role=Role.USER, content=content)


@pytest.mark.asyncio
@respx.mock
async def test_health_ok():
    respx.get(f"{BASE}/api/tags").mock(return_value=httpx.Response(200, json={}))
    p = OllamaProvider(base_url=BASE)
    try:
        assert await p.health() is True
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_health_failure():
    respx.get(f"{BASE}/api/tags").mock(side_effect=httpx.ConnectError("no"))
    p = OllamaProvider(base_url=BASE)
    try:
        assert await p.health() is False
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_chat_success():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": "hi there"}})
    )
    p = OllamaProvider(base_url=BASE)
    try:
        reply = await p.chat([_user()])
        assert reply == "hi there"
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_chat_model_not_found():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(404, json={"error": "model not found"})
    )
    p = OllamaProvider(base_url=BASE)
    try:
        with pytest.raises(ModelUnavailableError):
            await p.chat([_user()])
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_chat_malformed_body():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(200, json={"weird": True})
    )
    p = OllamaProvider(base_url=BASE)
    try:
        with pytest.raises(ModelResponseError):
            await p.chat([_user()])
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_chat_connection_error():
    respx.post(f"{BASE}/api/chat").mock(side_effect=httpx.ConnectError("no"))
    p = OllamaProvider(base_url=BASE)
    try:
        with pytest.raises(ProviderConnectionError):
            await p.chat([_user()])
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_stream_chunks():
    body = (
        b'{"message":{"content":"Hel"},"done":false}\n'
        b'{"message":{"content":"lo"},"done":false}\n'
        b'{"message":{"content":""},"done":true}\n'
    )
    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(200, content=body)
    )
    p = OllamaProvider(base_url=BASE)
    try:
        chunks = [c async for c in p.stream([_user()])]
        assert "".join(chunks) == "Hello"
    finally:
        await p.close()
