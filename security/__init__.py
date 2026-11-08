"""SARATHI security primitives.

V0.2 provides only the path allowlist guard. The full permission system
with confirmation gates, audit log, and emergency stop arrives in V0.4.
"""

from security.paths import resolve_under_roots

__all__ = ["resolve_under_roots"]
