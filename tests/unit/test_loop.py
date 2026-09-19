import pytest
from typing import Any
from sarathi.core.types import Context, ModelResponse, ToolCall, ToolResult, Usage, Tier, Trust
from sarathi.agents.loop import Agent, RunResult

class MockProvider:
    def __init__(self, script: list[ModelResponse]):
        self.script = script
        self.calls = 0

    async def complete(self, messages, spec, tools=None, ctx=None, task_type=None, temperature=0.7) -> ModelResponse:
        if self.calls < len(self.script):
            resp = self.script[self.calls]
            self.calls += 1
            return resp
        return ModelResponse(text="Mock exhausted")

class MockGateway:
    def __init__(self, responses: dict[str, ToolResult]):
        self.responses = responses

    async def execute(self, call, ctx) -> ToolResult:
        if call.name in self.responses:
            return self.responses[call.name]
        return ToolResult.failed(call.id, "Mock not found")

class MockRegistry:
    def permitted(self, ctx) -> list:
        return []

@pytest.mark.asyncio
async def test_normal_read_answer():
    provider = MockProvider([
        ModelResponse(
            tool_calls=[ToolCall(id="1", name="read_file", args={"path": "note.txt"})],
            usage=Usage(input_tokens=150, output_tokens=50, cost_inr=0.1)
        ),
        ModelResponse(text="Sarathi uses SQLite for memory.", usage=Usage(input_tokens=200, output_tokens=10, cost_inr=0.05))
    ])
    gateway = MockGateway({
        "read_file": ToolResult(call_id="1", ok=True, content="SQLite memory notes")
    })
    
    agent = Agent(provider, None, MockRegistry(), gateway, "System prompt")
    ctx = Context(session_id="test")
    
    res = await agent.run("What does Sarathi use for memory?", ctx)
    assert res.status == "done"
    assert res.content == "Sarathi uses SQLite for memory."
    assert len(res.trace) == 1
    assert res.trace[0][0] == "read_file"

@pytest.mark.asyncio
async def test_loop_stalled():
    # Model repeats the same tool call with same arguments
    provider = MockProvider([
        ModelResponse(tool_calls=[ToolCall(id="1", name="fetch_url", args={"url": "http"})]),
        ModelResponse(tool_calls=[ToolCall(id="2", name="fetch_url", args={"url": "http"})]),
        ModelResponse(tool_calls=[ToolCall(id="3", name="fetch_url", args={"url": "http"})]),
        ModelResponse(tool_calls=[ToolCall(id="4", name="fetch_url", args={"url": "http"})])
    ])
    gateway = MockGateway({
        "fetch_url": ToolResult(call_id="id", ok=False, content="ERROR")
    })
    
    agent = Agent(provider, None, MockRegistry(), gateway, "System prompt")
    ctx = Context(session_id="test")
    # By default max_stalls = 3
    res = await agent.run("Do it", ctx)
    assert res.status == "stalled"
    assert "repeated identical actions" in res.content

@pytest.mark.asyncio
async def test_budget_exceeded():
    # Model does different tool calls infinitely
    script = []
    for i in range(20):
        script.append(ModelResponse(tool_calls=[ToolCall(id=str(i), name="fetch_url", args={"url": str(i)})]))
    
    provider = MockProvider(script)
    gateway = MockGateway({"fetch_url": ToolResult(call_id="id", ok=True, content="ok")})
    
    agent = Agent(provider, None, MockRegistry(), gateway, "System")
    ctx = Context(session_id="test")
    ctx.budget.max_steps = 5 # Force early stop
    
    res = await agent.run("Do it", ctx)
    assert res.status == "budget"
    assert "step limit" in res.content
