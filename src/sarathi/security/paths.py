"""Path authorisation.

One guarantee: a tool can never touch a file outside the roots you allowed,
no matter what string the model produced.

THE ORDERING RULE: canonicalise FIRST (resolve ~, .., symlinks), THEN check.
Checking the raw string lets ../../../.ssh/id_rsa and symlink escapes walk
straight past an allowlist that looks correct.
"""
from __future__ import annotations
import fnmatch
from pathlib import Path


class PolicyDenied(Exception):
    """Refusal. Caught by the gateway, shown to the model as an observation."""


def _expand(p: str | Path) -> Path:
    return Path(p).expanduser().resolve(strict=False)


def _is_within(child: Path, root: Path) -> bool:
    return child == root or root in child.parents


class PathPolicy:
    def __init__(self, allow_read, allow_write, deny_roots, deny_globs):
        self.allow_read  = [_expand(p) for p in allow_read]
        self.allow_write = [_expand(p) for p in allow_write]
        self.deny_roots  = [_expand(p) for p in deny_roots]
        self.deny_globs  = list(deny_globs)

    def check(self, raw: str, mode: str = "read") -> Path:
        p = _expand(raw)

        # 1. Denylist wins over everything, always.
        for root in self.deny_roots:
            if _is_within(p, root):
                raise PolicyDenied(f"inside denied directory: {root}")

        posix = p.as_posix()
        for pattern in self.deny_globs:
            if fnmatch.fnmatch(p.name, pattern) or fnmatch.fnmatch(posix, pattern):
                raise PolicyDenied(f"matches denied pattern: {pattern}")

        # 2. Then the allowlist. Default deny.
        roots = self.allow_write if mode == "write" else self.allow_read
        for root in roots:
            if _is_within(p, root):
                return p
        raise PolicyDenied(f"outside allowed roots for {mode}: {p}")
