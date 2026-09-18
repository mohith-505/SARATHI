"""The agent loop. ~90 lines. This is the thing frameworks hide from you."""
from __future__ import annotations
from dataclasses import dataclass, field
from sarathi.core.types import (Budget, BudgetExceeded, Context, Message,
                                ModelResponse, Role, ToolResult)


@dataclass
class RunResult:
    status: str                       # done | budget | stalled | max_steps
    answer: str = ""
    trace: list = field(default_factory=list)
    budget_summary: str = ""


class Agent:
    def __init__(self, provider, spec, registry, gateway, system_prompt: str) -> None:
        self.provider, self.spec = provider, spec
        self.registry, self.gateway = registry, gateway
        self.system_prompt = system_prompt

    async def run(self, goal: str, ctx: Context) -> RunResult:
        messages = [Message(role=Role.SYSTEM, content=self.system_prompt),
                    Message(role=Role.USER, content=goal)]
        trace, stalls, last_sig = [], 0, None

        while True:
            try:
                ctx.budget.check()
            except BudgetExceeded as e:
                return RunResult("budget", f"Stopped: {e}", trace, ctx.budget.summary())
            ctx.budget.tick()

            resp: ModelResponse = await self.provider.complete(
                messages, self.spec, tools=self.registry.permitted(ctx))
            ctx.budget.charge(resp.usage)

            if resp.is_final:
                return RunResult("done", resp.text, trace, ctx.budget.summary())

            messages.append(Message(role=Role.ASSISTANT,
                                    content=resp.text or "[tool calls]"))
            for call in resp.tool_calls:
                result: ToolResult = await self.gateway.execute(call, ctx)
                trace.append((call.name, result.ok, result.content[:200]))
                messages.append(Message(role=Role.TOOL, name=call.name,
                                        tool_call_id=call.id, content=result.content,
                                        trust=result.trust))

            # PROGRESS CHECK - the thing that stops infinite loops.
            # Signature of what just happened; if it repeats, we are thrashing.
            sig = tuple((c.name, str(sorted(c.args.items()))) for c in resp.tool_calls)
            stalls = stalls + 1 if sig == last_sig else 0
            last_sig = sig
            if stalls >= 1:
                messages.append(Message(role=Role.USER, content=(
                    "You just repeated the same tool call with identical arguments. "
                    "State why the previous attempt did not work, then take a "
                    "DIFFERENT approach or give your best answer with what you have.")))
            if stalls >= ctx.budget.max_stalls:
                return RunResult("stalled", "Stopped: repeated identical actions.",
                                 trace, ctx.budget.summary())
