# SARATHI Security Model

## Permanent Invariants (Non-Negotiable Architecture Rules)

These rules are permanent architectural constraints, not temporary phase limitations:

1. **Security Policy Immobility**:
   The model must NEVER be able to modify, loosen, reconfigure, or override its own security policy, permission tiers, allowed workspace roots, or tool whitelists. Policy configuration is strictly server-side authoritative.

2. **No Self-Approval of Privileged Actions**:
   The model cannot approve its own privileged actions or bypass server-side confirmation and authorization gates. Permissions (`granted_permissions`) originate exclusively from trusted host configuration, never from LLM output, WebSocket client parameters, or user prompts.

3. **Unbypassable Emergency Stop**:
   The emergency stop is a hard hardware/software circuit breaker. When active, all model execution loops, tool invocations, and agent turns are immediately halted and rejected. The emergency stop state can only be cleared by an explicit host operator action—never by the model or an untrusted client call.

4. **Strict Localhost Isolation**:
   The SARATHI daemon binds exclusively to `127.0.0.1`. The HUD and daemon must not be exposed to untrusted network clients.

5. **Phase 1 Lean Persistence (Deferred Vector Memory)**:
   Phase 1 explicitly defers `sqlite-vec` and semantic/vector embeddings. Persistence is strictly SQLite (`aiosqlite`) for sessions, messages, and audit metadata. Semantic search and vector memory land in subsequent phases once the core conversation, tool execution, and voice pipeline are fully stabilized.

## Permission Tiers

- **T0 (Information)**: Safe read-only inspections (`fs.list`, `fs.read`, `web.search`, system time). Strictly bounded to workspace directories.
- **T1 (Safe Actions)**: Local sandboxed operations that do not modify system state.
- **T2 (Potentially Destructive)**: File modifications, package installs. Requires explicit user/operator confirmation.
- **T3 (Critical / Privileged)**: System-level modifications, shell commands, secrets access. Requires explicit confirmation every time with full parameter audit.

## Path & Filesystem Boundaries

- All filesystem operations are strictly resolved and checked against declared roots / workspace via `safe_path()`.
- Symbolic links pointing outside the workspace are rejected.
- Path traversal (`../`, absolute drive escapes like `C:\Windows\...`) is rejected with `PermissionError`.
- File reads enforce strict maximum byte sizes (default 200 KB) and UTF-8 encoding validation.
