"""SARATHI — Terminal Welcome.

Provides clean, minimal terminal branding without block ASCII art.
The primary visual experience is the high-fidelity graphical welcome screen.
"""

from __future__ import annotations

import sys
from rich.console import Console

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_terminal_welcome(console: Console | None = None, animate: bool = False) -> None:
    """Displays clean, minimal terminal branding without block ASCII art."""
    if console is None:
        console = Console()

    console.print(
        "\n[bold #00c8c8]SARATHI[/bold #00c8c8] [#d9e3e8]~ Your AI Companion[/#d9e3e8]  "
        "[dim #5c7c8c]•  Guiding Your Ideas Forward[/dim #5c7c8c]\n"
    )


if __name__ == "__main__":
    console = Console()
    print_terminal_welcome(console)
