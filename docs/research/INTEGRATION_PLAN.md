# SARATHI Integration Plan

Based on the reference architectures audited, here is the plan to integrate useful components into SARATHI's phases:

## Phase 1: Foundation
- **Octop's Single-Process Model**: Adopt Octop's single-process model (`FastAPI` + `uvicorn`) and environment configuration to ensure simple deployment on Windows.
- **Storage**: Use local SQLite for metadata (borrowed from Octop) rather than in-memory or unstructured logs.

## Phase 2: Memory & Context
- **Markdown-based Memory**: Adapt the concept of Obsidian-vault style memory from `harry-ai`. Storing user context in readable markdown files makes memory transparent and easily editable.
- **Hierarchical Storage**: Adapt Octop's hierarchical memory patterns for long-term state retention.

## Phase 3: Skills & Tools
- **Skill Registry**: Adapt `harry-ai`'s skill registry concept for organizing a large catalogue of triggers.
- **Tool Guardrails**: Adopt Octop's `tool_guard` architecture. Since SARATHI is Windows-first, unsafe subprocesses must be strictly gated. Octop's explicit approval system for shell commands is ideal.

## Phase 4: UI / UX
- **Desktop Client**: Follow Octop's pattern of providing a web dashboard coupled with a lightweight local wrapper for the desktop client. 
- **Avoid Dummy Architectures**: Completely reject the `jarvis` WebSocket relay placeholder pattern. All WS communication should carry semantic LLM payloads.

## Phase 5: ACP & Integration
- **Agent Client Protocol (ACP)**: Adopt Octop's implementation of MCP and ACP for inbound/outbound IDE integrations. This will allow SARATHI to natively integrate with IDEs (like VS Code or Cursor) on Windows.

## Phase 6: Agentic Coding
- **Workspace Isolation**: Utilize Octop's architecture for isolating agent workspaces (`~/.octop/agents/<agent_id>/`).
- **Executors**: Avoid `clickclickclick`'s macOS/Android specific executors. SARATHI must build Windows-native executors using secure, bound subprocesses rather than unrestricted `pyautogui` or AppleScript.

## Phase 7: Optimization & Automation
- **Cron Automation**: Utilize Octop's APScheduler-based cron scheduling to handle proactive, scheduled tasks natively within the main loop.
