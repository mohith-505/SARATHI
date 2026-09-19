import asyncio
import typer
from rich.console import Console
from rich.panel import Panel

from sarathi.core.config import config, secrets
from sarathi.core.types import Context, Role, ModelSpec, RouteRequest, Tier
from sarathi.models.openai_compat import OpenAICompatProvider
from sarathi.models.router import Router
from sarathi.models.base import ModelClient
from sarathi.security.paths import PathPolicy
from sarathi.security.audit import AuditLogger
from sarathi.tools.registry import Registry
from sarathi.tools.gateway import Gateway
from sarathi.tools.impl.fs import ReadFileTool, ListDirTool, SearchFilesTool
from sarathi.tools.impl.sandbox import PythonExecTool, RunShellTool
from sarathi.agents.loop import Agent
import sarathi.memory.db as db_module
import uuid
import yaml

app = typer.Typer(help="Project Sarathi CLI")
console = Console()

async def mock_approve(tool_name: str, args: dict) -> bool:
    console.print(f"\n[bold yellow]APPROVAL REQUIRED[/bold yellow]")
    console.print(f"Tool: {tool_name}")
    console.print(f"Args: {args}")
    resp = console.input("Allow this execution? (y/N): ")
    return resp.strip().lower() == "y"

async def async_chat(model_key: str):
    console.print(Panel(
        f"[bold green]Sarathi Agent[/bold green]\nTarget: {model_key}\nType /exit to quit.", 
        border_style="green"
    ))
    
    # 1. DB & Audit
    db_conn = db_module.init_db(config.paths.db, "src/sarathi/memory/schema.sql")
    audit = AuditLogger(db_conn)
    
    # 2. Security Policy
    import yaml
    with open("src/sarathi/security/policies.yaml", "r") as f:
        pol_config = yaml.safe_load(f)
        
    policy = PathPolicy(
        allow_read=pol_config["paths"]["allow_read"],
        allow_write=pol_config["paths"]["allow_write"],
        deny_roots=pol_config["paths"]["deny_roots"],
        deny_globs=pol_config["paths"]["deny_globs"],
    )
    
    # 3. Registry & Tools
    registry = Registry()
    registry.register(ReadFileTool(policy))
    registry.register(ListDirTool(policy))
    registry.register(SearchFilesTool(policy))
    registry.register(PythonExecTool())
    registry.register(RunShellTool(
        allow_binaries=pol_config["shell"]["allow_binaries"],
        deny_patterns=pol_config["shell"]["deny_patterns"]
    ))
    
    gateway = Gateway(registry, mock_approve, audit)
    
    # 4. Providers & Router
    local_provider = OpenAICompatProvider(base_url="http://localhost:11434/v1")
    cloud_provider = OpenAICompatProvider(
        base_url="https://openrouter.ai/api/v1", 
        api_key=secrets.openrouter_api_key
    )
    
    local_specs = [ModelSpec(**s) for s in config.models.get("local", [])]
    cloud_specs = {k: ModelSpec(**v) for k, v in config.models.get("cloud", {}).items()}
    router = Router(local=local_specs, cloud=cloud_specs)
    
    session_id = str(uuid.uuid4())
    
    system_prompt = "You are Sarathi. Use tools to fulfill requests."
    try:
        with open("profile.md", "r") as f:
            system_prompt += "\n\n" + f.read()
    except FileNotFoundError:
        pass
        
    while True:
        try:
            user_input = console.input("\n[bold blue]You:[/bold blue] ")
            if not user_input.strip():
                continue
            if user_input.strip() == "/exit":
                break
                
            # Route request
            req = RouteRequest()
            if model_key == "local":
                req.offline = True
                
            spec = router.route(req)
            provider = local_provider if spec.is_local else cloud_provider
            client = ModelClient(provider, db_conn)
            
            agent = Agent(client, spec, registry, gateway, system_prompt)
            ctx = Context(session_id=session_id, session_tier=Tier.T2)
            
            with console.status(f"Agent running ({spec.name})..."):
                res = await agent.run(user_input, ctx)
                
            if res.status == "done":
                console.print(f"[bold purple]Sarathi:[/bold purple] {res.content}")
            else:
                console.print(f"[bold red]Stopped ({res.status}):[/bold red] {res.content}")
                
            if res.trace:
                console.print("[dim]Trace:[/dim]")
                for t in res.trace:
                    console.print(f"[dim]  - {t[0]} (ok={t[1]})[/dim]")
            
            console.print(f"[dim]Budget: {res.budget_summary}[/dim]")
            
        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            console.print(f"[bold red]System Error:[/bold red] {type(e).__name__}: {str(e) or 'No details'}")

@app.command()
def chat(model: str = typer.Option("local", help="Model to use (local, cloud)")):
    asyncio.run(async_chat(model))

@app.command(name="eval")
def run_eval():
    '''Run the eval suite.'''
    with open('evals/suites/core.yaml', 'r') as f:
        suites = yaml.safe_load(f)
    
    from rich.table import Table
    table = Table(title="Eval Results")
    table.add_column("ID", style="cyan")
    table.add_column("Goal", style="magenta")
    table.add_column("Status", style="green")
    
    for suite in suites:
        table.add_row(suite['id'], suite['goal'], "[yellow]SKIP (Mock)[/yellow]")
    
    console.print(table)

if __name__ == "__main__":
    app()
