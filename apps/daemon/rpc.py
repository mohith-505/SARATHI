"""JSON-RPC 2.0 WebSocket Handler for SARATHI Daemon (Phase 2 Interactive Agent).

Enforces permanent invariants:
- Model/client cannot alter security policy or self-approve.
- Emergency stop halts all processing immediately and cancels pending approvals.
- Privileged tools (T2+) require interactive user confirmation via chat.approval_request.
- Emits chat.delta notifications for real-time token streaming.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import WebSocket

from apps.daemon.core_runtime import (
    is_emergency_stop_active,
    reset_emergency_stop,
    trigger_emergency_stop,
)
from core.agent.agent import Agent
from core.config.settings import SarathiSettings
from core.logging.logger import get_logger
from core.memory.vault import MemoryVault
from core.storage.sqlite import SQLiteStore
from core.types.messages import Message, Role
from models.providers.ollama_provider import OllamaProvider
from tools.factory import build_registry
from tools.registry import ToolRegistry

log = get_logger("daemon.rpc")


class RPCConnection:
    def __init__(self, websocket: WebSocket, store: SQLiteStore, settings: SarathiSettings):
        self.ws = websocket
        self.store = store
        self.settings = settings
        self.provider = OllamaProvider(
            base_url=settings.model.base_url,
            default_model=settings.model.name,
            temperature=settings.model.temperature,
            request_timeout=settings.model.request_timeout,
        )

        # Pending approval requests: approval_id -> Future[bool]
        self.pending_approvals: dict[str, asyncio.Future[bool]] = {}

        # Transparent Markdown Memory Vault
        self.vault = MemoryVault(settings.memory.vault_path, store)

        # Build tool registry with safe Phase 2 capabilities
        full_registry = build_registry(settings.tools, vault=self.vault)
        self.registry = ToolRegistry()
        allowed = {
            "fs.list",
            "fs.read",
            "fs.write",
            "fs.mkdir",
            "web.search",
            "system_information",
            "current_time",
            "terminal_safe",
            "application_launch",
            "filesystem_list",
            "filesystem_read",
            "filesystem_write",
            "directory_create",
            "web_search",
            "memory.save",
            "memory.read",
            "memory.search",
            "memory.list",
            "memory_save",
            "memory_read",
            "memory_search",
            "memory_list",
        }
        for name in allowed:
            if name in full_registry:
                tool = full_registry.get(name)
                self.registry.register(tool, as_name=name)

        self.agent = Agent(
            self.provider,
            self.settings,
            registry=self.registry,
            confirm=self.confirm_callback,
        )

    async def confirm_callback(
        self, tool_name: str, description: str, args: dict[str, Any]
    ) -> bool:
        """Send approval request to HUD for T2+ privileged actions and await user response."""
        if is_emergency_stop_active():
            return False

        approval_id = str(uuid.uuid4())
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        self.pending_approvals[approval_id] = future

        tool = self.agent.registry.get(tool_name) if self.agent.registry else None
        perm_level = tool.permission_level.name if tool else "T2"

        log.info("Requesting approval [%s] for %s (%s)", approval_id, tool_name, perm_level)

        await self.send_notification(
            "chat.approval_request",
            {
                "approval_id": approval_id,
                "tool": tool_name,
                "description": description,
                "arguments": args,
                "permission_level": perm_level,
            },
        )

        try:
            # 60s timeout for user confirmation
            approved = await asyncio.wait_for(future, timeout=60.0)
            log.info("Approval [%s] decision: %s", approval_id, approved)
            return approved
        except (TimeoutError, asyncio.CancelledError):
            log.warning("Approval [%s] timed out or was cancelled.", approval_id)
            return False
        finally:
            self.pending_approvals.pop(approval_id, None)

    async def send_response(self, req_id: Any, result: Any) -> None:
        payload = {"jsonrpc": "2.0", "result": result, "id": req_id}
        await self.ws.send_text(json.dumps(payload))

    async def send_error(self, req_id: Any, code: int, message: str) -> None:
        payload = {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": req_id}
        await self.ws.send_text(json.dumps(payload))

    async def send_notification(self, method: str, params: Any) -> None:
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        await self.ws.send_text(json.dumps(payload))

    async def handle_message(self, text: str) -> None:
        try:
            req = json.loads(text)
        except json.JSONDecodeError:
            await self.send_error(None, -32700, "Parse error")
            return

        if not isinstance(req, dict) or req.get("jsonrpc") != "2.0":
            req_id = req.get("id") if isinstance(req, dict) else None
            await self.send_error(req_id, -32600, "Invalid Request")
            return

        method = req.get("method")
        params = req.get("params") or {}
        req_id = req.get("id")

        # Emergency Stop Controls
        if method == "emergency_stop.trigger":
            trigger_emergency_stop()
            # Cancel any pending approval requests immediately
            for pending_fut in self.pending_approvals.values():
                if not pending_fut.done():
                    pending_fut.set_result(False)
            self.pending_approvals.clear()
            await self.send_response(
                req_id, {"status": "emergency_stop_triggered", "active": True}
            )
            return
        elif method == "emergency_stop.reset":
            reset_emergency_stop()
            await self.send_response(
                req_id, {"status": "emergency_stop_reset", "active": False}
            )
            return
        elif method == "emergency_stop.status":
            await self.send_response(req_id, {"active": is_emergency_stop_active()})
            return

        # Interactive Tool Approval Response from HUD
        if method == "chat.approval_response":
            approval_id = params.get("approval_id")
            approved = bool(params.get("approved", False))
            fut: asyncio.Future[bool] | None = (
                self.pending_approvals.get(approval_id) if isinstance(approval_id, str) else None
            )
            if fut is not None and not fut.done():
                fut.set_result(approved)
                await self.send_response(
                    req_id, {"status": "ok", "approval_id": approval_id, "approved": approved}
                )
            else:
                await self.send_error(req_id, -32602, "Approval request not found or expired")
            return

        # Check circuit breaker before processing agent turns
        if is_emergency_stop_active():
            await self.send_error(req_id, -32000, "Emergency stop is active. Operations halted.")
            return

        if method == "memory.list":
            category = params.get("category")
            cat_str = str(category) if category else None
            entries = await self.vault.list_entries(category=cat_str)
            await self.send_response(req_id, {"entries": entries, "count": len(entries)})
            return

        elif method == "memory.search":
            query = params.get("query", "")
            raw_limit = params.get("limit", 10)
            limit = int(raw_limit) if isinstance(raw_limit, (int, str)) else 10
            entries = await self.vault.search_entries(str(query), limit=limit)
            await self.send_response(
                req_id, {"query": str(query), "results": entries, "count": len(entries)}
            )
            return

        elif method == "memory.save":
            key = params.get("key")
            content = params.get("content")
            category = params.get("category", "fact")
            if not isinstance(key, str) or not isinstance(content, str):
                await self.send_error(req_id, -32602, "Missing or invalid key/content")
                return
            cat_str = str(category) if category else "fact"
            res = await self.vault.save_entry(key, content, cat_str)
            summary = await self.vault.get_context_summary()
            self.agent.update_memory_context(summary)
            await self.send_response(req_id, {"status": "ok", "entry": res})
            return

        elif method == "sessions.list":
            sessions = await self.store.list_sessions()
            await self.send_response(req_id, {"sessions": sessions})

        elif method == "session.load":
            session_id = params.get("session_id")
            if not session_id:
                await self.send_error(req_id, -32602, "Missing session_id")
                return
            messages = await self.store.get_messages(session_id)

            # Load into agent
            self.agent.reset()
            if self.settings.memory.enabled and self.settings.memory.auto_inject:
                mem_ctx = await self.vault.get_context_summary()
                self.agent.update_memory_context(mem_ctx)
            loaded_msgs = [m for m in messages if m.role != Role.SYSTEM]
            self.agent.conversation.messages.extend(loaded_msgs)

            formatted_msgs = [
                {
                    "role": m.role.value,
                    "content": m.content,
                    "name": m.name,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in loaded_msgs
            ]
            await self.send_response(
                req_id,
                {"session_id": session_id, "messages": formatted_msgs},
            )

        elif method == "chat.send":
            session_id = params.get("session_id") or "default"
            raw_text = params.get("message") or params.get("text")
            user_text = raw_text.strip() if isinstance(raw_text, str) else ""

            if not user_text:
                await self.send_error(req_id, -32602, "Missing or empty message/text")
                return

            # Ensure session in DB
            await self.store.ensure_session(session_id, title=user_text[:30] + "...")

            user_msg = Message(role=Role.USER, content=user_text)
            await self.store.save_message(session_id, user_msg)
            self.agent.conversation.add_user(user_text)

            if self.settings.memory.enabled and self.settings.memory.auto_inject:
                await self.vault.bootstrap()
                mem_ctx = await self.vault.get_context_summary()
                self.agent.update_memory_context(mem_ctx)

            try:
                max_iter = self.settings.agent.max_tool_iterations
                for iteration in range(max_iter):
                    if is_emergency_stop_active():
                        await self.send_error(req_id, -32000, "Emergency stop triggered.")
                        return

                    step_status = f"thinking (step {iteration+1})"
                    await self.send_notification("chat.status", {"status": step_status})

                    buffer: list[str] = []
                    await self.send_notification(
                        "chat.stream.start", {"session_id": session_id}
                    )

                    async for chunk in self.provider.stream(
                        self.agent.conversation.messages, model=self.settings.model.name
                    ):
                        if is_emergency_stop_active():
                            await self.send_error(
                                req_id, -32000, "Emergency stop triggered during stream."
                            )
                            return
                        buffer.append(chunk)
                        # HUD streaming protocol: chat.delta with id and text
                        await self.send_notification(
                            "chat.delta",
                            {"id": req_id, "text": chunk},
                        )
                        # Backwards compatibility notification
                        await self.send_notification("chat.stream.chunk", {"chunk": chunk})

                    response_text = "".join(buffer)
                    await self.send_notification("chat.stream.end", {})

                    tool_call = self.agent._parse_tool_call(response_text)

                    if tool_call is None:
                        # Final plain answer
                        self.agent.conversation.add_assistant(response_text)
                        assistant_msg = Message(role=Role.ASSISTANT, content=response_text)
                        await self.store.save_message(session_id, assistant_msg)
                        self.agent._trim_history()

                        await self.send_response(
                            req_id,
                            {
                                "session_id": session_id,
                                "content": response_text,
                                "reply": response_text,
                                "done": True,
                            },
                        )
                        return

                    # Model emitted a tool call: record assistant turn first
                    name, t_args = tool_call
                    self.agent.conversation.add_assistant(response_text)
                    assistant_call_msg = Message(role=Role.ASSISTANT, content=response_text)
                    await self.store.save_message(session_id, assistant_call_msg)

                    await self.send_notification(
                        "chat.status", {"status": f"executing tool {name}"}
                    )

                    # Execute tool through agent's permission-checked executor
                    result_obj = await self.agent._execute_tool(name, t_args)
                    result_data = result_obj.to_json()

                    tool_msg = Message(
                        role=Role.TOOL,
                        content=json.dumps(result_data, ensure_ascii=False),
                        name=name,
                    )
                    self.agent.conversation.messages.append(tool_msg)
                    await self.store.save_message(session_id, tool_msg)
                    self.agent._trim_history()

                    if name in {"memory_save", "memory.save"}:
                        mem_ctx = await self.vault.get_context_summary()
                        self.agent.update_memory_context(mem_ctx)

                # Hit max iterations
                final = "Reached maximum tool iterations without final answer."
                self.agent.conversation.add_assistant(final)
                final_msg = Message(role=Role.ASSISTANT, content=final)
                await self.store.save_message(session_id, final_msg)
                await self.send_response(
                    req_id,
                    {
                        "session_id": session_id,
                        "content": final,
                        "reply": final,
                        "done": True,
                    },
                )

            except Exception as e:
                log.exception("Chat failed: %s", e)
                # Never store a failed/incomplete answer as a completed one
                await self.send_error(req_id, -32000, f"Model error: {e}")

        else:
            await self.send_error(req_id, -32601, f"Method not found: {method}")
