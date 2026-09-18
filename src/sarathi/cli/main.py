import asyncio
import typer
from rich.console import Console
from rich.panel import Panel

from sarathi.core.config import config, secrets
from sarathi.core.types import Message, Role, ModelSpec
from sarathi.models.openai_compat import OpenAICompatProvider

app = typer.Typer(help="Project Sarathi CLI")
console = Console()

async def async_chat(model_key: str):
    console.print(Panel(
        f"[bold green]Sarathi Chat[/bold green]\nTarget: {model_key}\nType /exit to quit, /model <name> to switch.", 
        border_style="green"
    ))
    
    messages = []
    current_model_key = model_key
    
    # Initialize providers (mock URLs for now unless configured)
    local_provider = OpenAICompatProvider(base_url="http://localhost:11434/v1")
    cloud_provider = OpenAICompatProvider(
        base_url="https://openrouter.ai/api/v1", 
        api_key=secrets.openrouter_api_key
    )

    while True:
        try:
            user_input = console.input("[bold blue]You:[/bold blue] ")
            if not user_input.strip():
                continue
            
            if user_input.strip() == "/exit":
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if user_input.startswith("/model "):
                current_model_key = user_input.split(" ", 1)[1].strip()
                console.print(f"[green]Switched model to: {current_model_key}[/green]")
                continue
                
            messages.append(Message(role=Role.USER, content=user_input))
            
            # Determine spec and provider
            is_local = current_model_key == "local"
            
            if is_local:
                # Grab the first local model from config
                spec_data = config.models.get("local", [{}])[0]
                provider = local_provider
            else:
                # Grab the cloud model
                spec_data = config.models.get("cloud", {}).get(current_model_key, {})
                provider = cloud_provider
                
            if not spec_data:
                console.print(f"[red]Error: Model '{current_model_key}' not found in config.yaml[/red]")
                messages.pop() # remove the user message so we can retry
                continue

            spec = ModelSpec(**spec_data)
            
            console.print(f"[bold purple]Sarathi ({spec.name}):[/bold purple] ", end="")
            
            # Note: For Day 5, we use the complete() method which is non-streaming in our Day 3 implementation.
            # To add streaming, the provider would need a stream() method, but we'll stick to complete()
            # for now to satisfy the "runs against local/cloud" requirement.
            with console.status("Thinking..."):
                resp = await provider.complete(messages, spec)
                
            console.print(resp.text)
            messages.append(Message(role=Role.ASSISTANT, content=resp.text))
            
            # Show token counts
            console.print(f"[dim]Usage: {resp.usage.input_tokens} in / {resp.usage.output_tokens} out[/dim]")
            
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Exiting...[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")

@app.command()
def chat(model: str = typer.Option("local", help="Model to use (local, mid, reasoning, coding)")):
    """Start an interactive chat session."""
    asyncio.run(async_chat(model))

if __name__ == "__main__":
    app()
