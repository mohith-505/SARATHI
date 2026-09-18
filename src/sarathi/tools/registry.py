from typing import Any, Protocol, Type
from pydantic import BaseModel
from sarathi.core.types import Context, Tier, Trust

class Tool(Protocol):
    name: str
    description: str
    tier: Tier
    output_trust: Trust
    schema: Type[BaseModel]

    async def run(self, args: BaseModel, ctx: Context) -> str:
        ...

class Registry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def permitted(self, ctx: Context) -> list[dict[str, Any]]:
        cap = Tier.T1 if ctx.untrusted_seen else ctx.session_tier
        api_tools = []
        for t in self._tools.values():
            if t.tier <= cap:
                api_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.schema.model_json_schema()
                    }
                })
        return api_tools
