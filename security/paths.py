"""Minimal path allowlist guard for V0.2.

The full security module (permission tiers with audit logging, keyring
integration, emergency stop) arrives in V0.4. This module only enforces
that filesystem tools stay within declared roots.
"""

from __future__ import annotations

from pathlib import Path

from core.errors.exceptions import PathAccessError


def resolve_under_roots(path: str | Path, allowed_roots: list[Path]) -> Path:
    """Resolve ``path`` and confirm it lives under one of ``allowed_roots``.

    - Relative paths are resolved against the current working directory.
    - ``~`` is expanded.
    - Symlinks are resolved before comparison (escape via symlink is blocked).
    - Nonexistent paths are allowed only for tools that create them
      (resolution uses ``strict=False``).
    """
    if not allowed_roots:
        raise PathAccessError("No allowed roots configured.")

    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p

    try:
        resolved = p.resolve(strict=False)
    except OSError as e:
        raise PathAccessError(f"Cannot resolve path {path!r}: {e}") from e

    for root in allowed_roots:
        try:
            root_resolved = Path(root).expanduser().resolve(strict=False)
        except OSError:
            continue
        try:
            resolved.relative_to(root_resolved)
            return resolved
        except ValueError:
            continue

    raise PathAccessError(
        f"Path {resolved} is outside allowed roots: "
        + ", ".join(str(Path(r).expanduser()) for r in allowed_roots)
    )
