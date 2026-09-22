import asyncio
from sarathi.models.openai_compat import OpenAICompatProvider
from sarathi.core.types import ModelSpec, Message, Role

async def test():
    provider = OpenAICompatProvider(base_url="http://localhost:11434/v1")
    spec = ModelSpec(name="qwen3:4b", provider="ollama")
    msgs = [Message(role=Role.USER, content="search for starter")]
    try:
        resp = await provider.complete(msgs, spec)
        print("Success:", resp.text)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
