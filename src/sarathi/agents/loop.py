from dataclasses import dataclass
from sarathi.core.types import Context, Message, Role, BudgetExceeded

@dataclass
class RunResult:
    status: str
    content: str
    trace: list
    budget_summary: str

class Agent:
    def __init__(self, provider, spec, registry, gateway, system_prompt):
        self.provider = provider
        self.spec = spec
        self.registry = registry
        self.gateway = gateway
        self.system_prompt = system_prompt

    async def run(self, goal: str, ctx: Context) -> RunResult:
        messages = [
            Message(role=Role.SYSTEM, content=self.system_prompt),
            Message(role=Role.USER, content=goal)
        ]
        trace, stalls, last_sig = [], 0, None

        while True:
            try:
                ctx.budget.check()
            except BudgetExceeded as e:
                return RunResult("budget", f"Stopped: {e}", trace, ctx.budget.summary())
            
            ctx.budget.tick()

            resp = await self.provider.complete(
                messages=messages, 
                spec=self.spec, 
                tools=self.registry.permitted(ctx),
                ctx=ctx,
                task_type="agent_loop"
            )
            ctx.budget.charge(resp.usage)

            if resp.is_final:
                return RunResult("done", resp.text, trace, ctx.budget.summary())

            # Log ASSISTANT response
            # Note: We don't have tool_calls in Message explicitly in our types right now unless we add it,
            # but we can rely on standard representation or the provider implementation.
            # For simplicity, we just put the text or "[tool calls]".
            messages.append(Message(role=Role.ASSISTANT, content=resp.text or "[tool calls]"))

            for call in resp.tool_calls:
                result = await self.gateway.execute(call, ctx)
                trace.append((call.name, result.ok, result.content[:200]))
                messages.append(Message(
                    role=Role.TOOL, 
                    name=call.name,
                    tool_call_id=call.id,
                    content=result.content, 
                    trust=result.trust
                ))

            # PROGRESS CHECK - stops infinite loops.
            sig = tuple((c.name, str(sorted(c.args.items()))) for c in resp.tool_calls)
            stalls = stalls + 1 if sig == last_sig else 0
            last_sig = sig
            
            if stalls >= 1:
                messages.append(Message(role=Role.USER, content=(
                    "You just repeated the same tool call with identical arguments. "
                    "State why the previous attempt did not work, then take a "
                    "DIFFERENT approach or answer with what you have.")))
            
            if stalls >= ctx.budget.max_stalls:
                return RunResult("stalled", "Stopped: repeated identical actions.",
                                 trace, ctx.budget.summary())
