"""THE ONLY PATH TO EXECUTION.

If any code anywhere else in Sarathi runs a tool, the security model is void.
Keep this file small enough that you can read it in one sitting and be sure.
"""
from __future__ import annotations
from typing import Callable, Awaitable
from pydantic import ValidationError
from sarathi.core.types import Context, Tier, ToolCall, ToolResult, Trust
from sarathi.security.paths import PolicyDenied
from sarathi.tools.registry import Registry

ApprovalFn = Callable[[str, dict], Awaitable[bool]]


class Gateway:
    def __init__(self, registry: Registry, approve: ApprovalFn, audit) -> None:
        self.registry = registry
        self.approve = approve
        self.audit = audit

    async def execute(self, call: ToolCall, ctx: Context) -> ToolResult:
        tool = self.registry.get(call.name)
        if tool is None:
            return ToolResult.failed(call.id, f"unknown tool {call.name!r}")

        # 1. SCHEMA VALIDATION - catches roughly half of all tool failures,
        #    and turns them into a message the model can actually act on.
        try:
            args = tool.schema.model_validate(call.args)
        except ValidationError as e:
            return ToolResult.failed(call.id, f"invalid arguments: {e.errors()}")

        # 2. TAINT CHECK - the mechanism that defuses indirect prompt injection.
        #    Once untrusted text is in context, this turn cannot reach T2+.
        if ctx.untrusted_seen and tool.tier > Tier.T1:
            self.audit.log(ctx, call, "denied", "taint")
            return ToolResult.denied(
                call.id, "untrusted content is in context; tier capped at T1 this turn")

        # 3. TIER CHECK
        if tool.tier > ctx.session_tier:
            self.audit.log(ctx, call, "denied", "tier")
            return ToolResult.denied(call.id, f"{tool.name} requires {tool.tier.name}")

        # 4. HUMAN APPROVAL - shows the LITERAL arguments. Never a summary:
        #    a summarised approval prompt IS the attack surface.
        if tool.tier >= Tier.T2:
            if not await self.approve(tool.name, args.model_dump()):
                self.audit.log(ctx, call, "rejected", "user")
                return ToolResult.denied(call.id, "user declined")

        # 5. EXECUTE
        self.audit.log(ctx, call, "allowed", "")
        try:
            out = await tool.run(args, ctx)
        except PolicyDenied as e:
            self.audit.log(ctx, call, "denied", str(e))
            return ToolResult.denied(call.id, str(e))
        except Exception as e:
            self.audit.log(ctx, call, "error", str(e))
            return ToolResult.failed(call.id, f"{type(e).__name__}: {e}")

        # 6. SANITISE + PROPAGATE TAINT
        limit = ctx.budget.tokens_per_observation * 4   # ~4 chars/token
        truncated = len(out) > limit
        if truncated:
            out = out[:limit] + f"\n...[truncated, {len(out)} chars total]"
        if tool.output_trust is Trust.UNTRUSTED:
            ctx.untrusted_seen = True
            out = f"<untrusted_content source={tool.name}>\n{out}\n</untrusted_content>"

        return ToolResult(call_id=call.id, ok=True, content=out,
                          trust=tool.output_trust, truncated=truncated)
