"""SARATHI CLI entry point (V0.2)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from core.agent.agent import Agent
from core.config.settings import SarathiSettings
from core.errors.exceptions import SarathiError
from core.logging.logger import configure_logging
from models.registry import create_provider
from tools.factory import build_registry
from tools.types import ToolResult
from apps.cli.terminal_welcome import print_terminal_welcome

app = typer.Typer(
    name="sarathi",
    help="SARATHI — Personal AI Operating Companion (V0.2 Tool System)",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True)





async def _chat_loop(settings: SarathiSettings) -> None:
    provider = create_provider(settings.model)

    healthy = await provider.health()
    if not healthy:
        console.print(
            Panel(
                f"[red]Cannot reach {settings.model.provider} at "
                f"{settings.model.base_url}.[/red]\n\n"
                "Checklist:\n"
                "  1. Start Ollama:      [bold]ollama serve[/bold]\n"
                f"  2. Pull the model:   [bold]ollama pull {settings.model.name}[/bold]\n"
                "  3. Re-run:            [bold]sarathi chat[/bold]",
                title="Provider unavailable",
                border_style="red",
            )
        )
        await provider.close()
        raise typer.Exit(code=2)

    registry = build_registry(settings.tools) if settings.tools.enabled else None

    ui_status = console.status("[dim]thinking...[/dim]", spinner="dots")

    async def on_tool_call(name: str, args: dict[str, Any]) -> None:
        console.print(
            f"[dim]→ tool[/dim] [bold]{name}[/bold] "
            f"[dim]{json.dumps(args, ensure_ascii=False)}[/dim]"
        )

    async def on_tool_result(name: str, result: ToolResult) -> None:
        status_text = "[green]ok[/green]" if result.success else "[red]fail[/red]"
        verified = " [cyan](verified)[/cyan]" if result.verified else ""
        console.print(f"[dim]← {status_text}{verified}[/dim]")
        if not result.success and result.error:
            console.print(f"[red]  {result.error}[/red]")

    async def confirm(name: str, description: str, args: dict[str, Any]) -> bool:
        ui_status.stop()
        try:
            console.print()
            console.print(
                Panel(
                    f"[yellow]Tool:[/yellow] {name}\n"
                    f"[dim]{description}[/dim]\n\n"
                    "[yellow]Arguments:[/yellow]\n"
                    f"{json.dumps(args, indent=2, ensure_ascii=False)}",
                    title="[bold yellow]Permission required[/bold yellow]",
                    border_style="yellow",
                )
            )
            answer = Prompt.ask("[yellow]Allow?[/yellow]", choices=["y", "n"], default="n")
            return answer == "y"
        finally:
            ui_status.start()

    agent = Agent(
        provider,
        settings,
        registry=registry,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
        confirm=confirm,
    )

    n_tools = len(registry) if registry else 0
    console.print(
        Panel(
            "[bold cyan]SARATHI V0.2 — Tool System[/bold cyan]\n"
            f"provider: [green]{settings.model.provider}[/green]   "
            f"model: [green]{settings.model.name}[/green]   "
            f"tools: [green]{n_tools}[/green]\n"
            "Commands: [bold]/reset[/bold] clear history   "
            "[bold]/tools[/bold] list tools   "
            "[bold]/exit[/bold] quit",
            border_style="cyan",
        )
    )

    try:
        while True:
            try:
                user = Prompt.ask("[bold blue]you[/bold blue]")
            except (EOFError, KeyboardInterrupt):
                console.print()
                break

            text = user.strip()
            if not text:
                continue
            if text.lower() in {"/exit", "/quit"}:
                break
            if text.lower() == "/reset":
                agent.reset()
                console.print("[yellow]Conversation reset.[/yellow]")
                continue
            if text.lower() == "/tools":
                if registry is None or len(registry) == 0:
                    console.print("[yellow]No tools registered.[/yellow]")
                else:
                    for t in registry.all():
                        console.print(
                            f"  [bold]{t.name}[/bold] "
                            f"[dim]({t.permission_level.name})[/dim] — {t.description}"
                        )
                continue

            console.print("[bold magenta]sarathi[/bold magenta]")
            try:
                ui_status.start()
                try:
                    reply = await agent.run(text)
                finally:
                    ui_status.stop()
                console.print(reply)
            except SarathiError as e:
                console.print(f"[red]Error:[/red] {e}")
            except Exception as e:  # noqa: BLE001
                console.print(f"[red]Unexpected error:[/red] {type(e).__name__}: {e}")
    finally:
        await provider.close()


@app.command()
def chat(
    config: Path = typer.Option(
        Path("config/default.toml"),
        "--config",
        "-c",
        help="Path to TOML config file.",
        show_default=True,
    ),
    log_level: str | None = typer.Option(
        None, "--log-level", help="Override log level."
    ),
    no_tools: bool = typer.Option(
        False, "--no-tools", help="Disable tools for this session."
    ),
) -> None:
    """Start an interactive chat session with SARATHI."""
    try:
        settings = SarathiSettings.load(config)
    except Exception as e:  # noqa: BLE001
        err_console.print(f"[red]Failed to load settings:[/red] {e}")
        raise typer.Exit(code=1) from e

    if log_level:
        settings.logging.level = log_level  # type: ignore[assignment]
    if no_tools:
        settings.tools.enabled = False

    configure_logging(settings.logging.level, settings.logging.file, force=True)
    print_terminal_welcome(console)

    try:
        asyncio.run(_chat_loop(settings))
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")


@app.command()
def version() -> None:
    """Print SARATHI version."""
    console.print("SARATHI v0.2.0 — Tool System")


@app.command()
def doctor(
    config: Path = typer.Option(
        Path("config/default.toml"), "--config", "-c", show_default=True
    ),
) -> None:
    """Check configuration, provider health, and tools."""
    try:
        settings = SarathiSettings.load(config)
    except Exception as e:  # noqa: BLE001
        err_console.print(f"[red]Failed to load settings:[/red] {e}")
        raise typer.Exit(code=1) from e

    console.print("[bold]SARATHI doctor[/bold]")
    console.print(f"  provider: {settings.model.provider}")
    console.print(f"  model:    {settings.model.name}")
    console.print(f"  base_url: {settings.model.base_url}")
    console.print(f"  timeout:  {settings.model.request_timeout}s")
    console.print(f"  log file: {settings.logging.file}")
    console.print(f"  tools:    {'enabled' if settings.tools.enabled else 'disabled'}")
    if settings.tools.enabled:
        for r in settings.tools.allowed_roots:
            console.print(f"    allowed root: {Path(r).expanduser()}")

    async def _check() -> bool:
        provider = create_provider(settings.model)
        try:
            return await provider.health()
        finally:
            await provider.close()

    ok = asyncio.run(_check())
    if ok:
        console.print("[green]Provider reachable.[/green]")
    else:
        console.print("[red]Provider unreachable.[/red]")
        raise typer.Exit(code=2)


@app.command()
def connect(
    service: str = typer.Argument(None, help="The service to connect (e.g. 'gdrive')"),
    list_all: bool = typer.Option(False, "--list", help="List connected services"),
) -> None:
    """Connect SARATHI to external tools and services via OAuth."""
    from connectors.google.auth import TOKEN_FILE

    if list_all:
        console.print("[bold]Connected Services:[/bold]")
        if TOKEN_FILE.exists():
            console.print("  [green]✓[/green] gdrive (Google Gmail/Calendar)")
        else:
            console.print("  [dim]No services connected.[/dim]")
        return

    if not service:
        console.print("[red]Error: Please specify a service to connect, or use --list.[/red]")
        raise typer.Exit(code=1)

    if service.lower() in ("gdrive", "google"):
        console.print("[cyan]Starting Google OAuth flow...[/cyan]")
        console.print("[dim]This will open a browser window to authenticate with Google.[/dim]")

        from connectors.google.auth import CREDENTIALS_FILE, authenticate
        # Default scopes for SARATHI (Gmail read-only, Calendar read-only)
        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]

        try:
            authenticate(scopes, force=True)
            console.print("[green]Successfully connected to Google![/green]")
        except FileNotFoundError:
            console.print(
                f"\n[red]Missing {CREDENTIALS_FILE}[/red]\n"
                "To connect to Google, you need an OAuth Client ID.\n"
                "1. Go to Google Cloud Console\n"
                "2. Create a Desktop App OAuth Client ID\n"
                f"3. Download the JSON and save it as: [bold]{CREDENTIALS_FILE}[/bold]\n"
                "4. Run this command again."
            )
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]Authentication failed:[/red] {e}")
            raise typer.Exit(code=1)
    else:
        console.print(f"[red]Unknown service: {service}[/red]")
        console.print("Supported services: gdrive")
        raise typer.Exit(code=1)




@app.command()
def welcome(
    gui: bool = typer.Option(False, "--gui", "-g", help="Launch graphical welcome window."),
) -> None:
    """Display the SARATHI reference-matched welcome experience."""
    if gui:
        from ui.welcome_window import main as run_gui
        run_gui()
    else:
        print_terminal_welcome(console)


if __name__ == "__main__":
    app()
