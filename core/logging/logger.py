"""Structured logging configuration for SARATHI."""

from __future__ import annotations

import logging
from pathlib import Path

from rich.logging import RichHandler

_ROOT_NAME = "sarathi"
_CONFIGURED = False


def configure_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    *,
    force: bool = False,
) -> logging.Logger:
    """Configure the ``sarathi`` logger tree.

    Idempotent unless ``force=True``. Attaches a Rich console handler and,
    optionally, a file handler.
    """
    global _CONFIGURED
    root = logging.getLogger(_ROOT_NAME)

    if _CONFIGURED and not force:
        return root

    root.handlers.clear()
    root.setLevel(level)
    root.propagate = False

    console = RichHandler(
        rich_tracebacks=True,
        show_time=False,
        show_path=False,
        markup=False,
    )
    console.setLevel(level)
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(fh)

    _CONFIGURED = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``sarathi`` namespace."""
    return logging.getLogger(f"{_ROOT_NAME}.{name}")
