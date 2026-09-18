"""Path authorisation.

The whole module exists to make one guarantee: a tool can never touch a file
outside the roots you allowed, no matter what string the model produced.

The ordering rule is the thing to internalise:
    canonicalise FIRST (resolve ~, .., and symlinks), THEN check.
Checking the raw string lets `../../../.ssh/id_rsa` and symlink escapes walk
straight past an allowlist that looks correct.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path


class PolicyDenied(Exception):
    """Raised when an action is refused. Caught by the gateway, surfaced to
    the model as an observation, never as a crash."""


def _expand(p: str) -> Path:
    return Path(p).expanduser().resolve(strict=False)


def _is_within(child: Path, root: Path) -> bool:
    return child == root or root in child.parents


class PathPolicy:
    """Immutable once constructed. Built from policies.yaml at startup."""

    def __init__(
        self,
        allow_read: list[str],
        allow_write: list[str],
        deny_roots: list[str],
        deny_globs: list[str],
    ) -> None:
        self.allow_read = [_expand(p) for p in allow_read]
        self.allow_write = [_expand(p) for p in allow_write]
        self.deny_roots = [_expand(p) for p in deny_roots]
        # Globs match against the filename AND the full posix path, so both
        # "*.pem" and "**/AppData/**" behave the way you would expect.
        self.deny_globs = list(deny_globs)

    def check(self, raw: str, mode: str = "read") -> Path:
        """Return the canonical path, or raise PolicyDenied."""
        if mode not in ("read", "write"):
            raise ValueError(f"bad mode {mode!r}")

        p = _expand(raw)

        # 1. Denylist wins over everything, always.
        for root in self.deny_roots:
            if _is_within(p, root):
                raise PolicyDenied(f"path is inside a denied directory: {root}")

        posix = p.as_posix()
        for pattern in self.deny_globs:
            if fnmatch.fnmatch(p.name, pattern) or fnmatch.fnmatch(posix, pattern):
                raise PolicyDenied(f"path matches denied pattern: {pattern}")

        # 2. Then the allowlist. Default deny.
        roots = self.allow_write if mode == "write" else self.allow_read
        for root in roots:
            if _is_within(p, root):
                return p

        raise PolicyDenied(f"path outside allowed roots for {mode}: {p}")

    def is_allowed(self, raw: str, mode: str = "read") -> bool:
        try:
            self.check(raw, mode)
            return True
        except PolicyDenied:
            return False
