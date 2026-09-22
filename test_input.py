import asyncio
from rich.console import Console

console = Console()

async def test():
    console.print("Testing input")
    resp = console.input("Allow? ")
    console.print(f"Got: {resp}")

asyncio.run(test())
