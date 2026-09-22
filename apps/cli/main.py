"""SARATHI CLI entry point (V0.1)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from core.agent.agent import Agent
from core.config.settings import SarathiSettings
from core.errors.exceptions import SarathiError
from core.logging.logger import configure_logging
from models.registry import create_provider

app = typer.Typer(
    name="sarathi",
    help="SARATHI — Personal AI Operating Companion (V0.1 Core Brain)",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True)


async def _chat_loop(settings: SarathiSettings) -> None:
    provider = create_provider(settings.model)
    agent = Agent(provider, settings)

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

    console.print(
        Panel(
            "[bold cyan]SARATHI V0.1 — Core Brain[/bold cyan]\n"
            f"provider: [green]{settings.model.provider}[/green]   "
            f"model: [green]{settings.model.name}[/green]\n"
            "Commands: [bold]/reset[/bold] clear history   "
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

            console.print("[bold magenta]sarathi[/bold magenta] ", end="")
            try:
                async for chunk in agent.stream(text):
                    console.print(chunk, end="", soft_wrap=True, highlight=False)
                console.print()
            except SarathiError as e:
                console.print(f"\n[red]Error:[/red] {e}")
            except Exception as e:  # noqa: BLE001
                console.print(f"\n[red]Unexpected error:[/red] {type(e).__name__}: {e}")
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
        None, "--log-level", help="Override log level (DEBUG/INFO/WARNING/ERROR)."
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

    configure_logging(settings.logging.level, settings.logging.file, force=True)

    try:
        asyncio.run(_chat_loop(settings))
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")


@app.command()
def version() -> None:
    """Print SARATHI version."""
    console.print("SARATHI v0.1.0 — Core Brain")


@app.command()
def doctor(
    config: Path = typer.Option(
        Path("config/default.toml"), "--config", "-c", show_default=True
    ),
) -> None:
    """Check configuration and provider health."""
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


if __name__ == "__main__":
    app()
