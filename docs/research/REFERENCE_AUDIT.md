# Reference Architecture Audit

## 1. Octop
- **Origin**: TencentCloud (GitHub: TencentCloud/Octop)
- **License**: MIT License
- **Dependencies**: Python 3.12+, FastAPI, uvicorn, React 18, octop-harness, octop-gateway, octop-memory, octop-browser, MCP, Playwright, SQLite/PostgreSQL.
- **Relevant File Paths**: `Octop-main/src/octop/`, `Octop-main/docs/`, `Octop-main/dashboard/`
- **Implementation Status**: Working implementation. Highly mature platform for multi-agent, multi-user deployment.
- **Dependency Conflicts & OS Compatibility**: Excellent Windows compatibility (mentions explicit support, powershell scripts, `subprocess_io_win` compat layer). No major conflicts.
- **Security & Risks**: Secure local storage (`~/.octop/secrets`), tool guardrails (`~/.octop/security/tool_guard/`) for subprocesses, explicit approval required for risky commands. Has terminal/shell AI+ and remote desktop which are powerful but isolated correctly.
- **Recommendation**: **ADOPT** core architectural patterns (single process, RAG memory, gateway) and **ADAPT** the ACP (Agent Client Protocol) for IDE integrations. **ADAPT** its tool guardrails for Windows.

## 2. clickclickclick
- **Origin**: InstaVM
- **License**: MIT License
- **Dependencies**: requests, pytest, pyautogui, fastapi, pillow, mlx, mlx-vlm, py-applescript.
- **Relevant File Paths**: `clickclickclick-main/main.py`, `clickclickclick-main/api.py`, `clickclickclick-main/clickclickclick/executor/`
- **Implementation Status**: Working but highly experimental implementation (CLI tool and FastAPI endpoint).
- **Dependency Conflicts & OS Compatibility**: Major conflict with Windows. It hard-requires `mlx` and `mlx-vlm` which are Apple Silicon (macOS) specific array frameworks. It uses `py-applescript` and OSX/Android specific executors (`MacExecutor`, `AndroidExecutor`). No Windows support.
- **Security & Risks**: Insecurely handles secrets by prompting the user and putting them directly in `os.environ` without persistence or a secure vault. Uses PyAutoGUI for unrestricted UI control.
- **Recommendation**: **REJECT** as a direct dependency due to OS incompatibilities and MLX lock-in. **DEFER** UI automation features until Windows-native executors are implemented.

## 3. harry-ai
- **Origin**: rudhrancodes-dev
- **License**: MIT License
- **Dependencies**: Resemblyzer (torch), fastapi, PyAudio, SpeechRecognition, pyobjc.
- **Relevant File Paths**: `harry-ai-main/harry/server.py`, `harry-ai-main/webapp/`, `harry-ai-main/harry/skills/registry.py`
- **Implementation Status**: Working but OS-specific implementation.
- **Dependency Conflicts & OS Compatibility**: macOS exclusively ("Voice-only agentic AI for macOS", uses AppleScript and `cliclick`, `pyobjc`). Will fail on Windows without heavy rewriting.
- **Security & Risks**: Unrestricted file access (`cliclick` and AppleScript for full machine control, code agent writes directly to `~/.harry/workspace/`). Uses an Obsidian vault for memory which is clever but unencrypted.
- **Recommendation**: **REJECT** codebase due to tight macOS coupling. **ADAPT** the 98-skill registry architecture and Obsidian-vault memory concept (plain markdown memory storage).

## 4. jarvis
- **Origin**: Unknown (generic MVP)
- **License**: Unspecified (assume proprietary/none, treat with caution)
- **Dependencies**: Next.js, React Three Fiber, Python FastAPI, uvicorn.
- **Relevant File Paths**: `jarvis-main/scripts/backend_server.py`, `jarvis-main/components/robot.tsx`
- **Implementation Status**: Demo / Placeholder. The backend merely relays string commands ("wave", "walk") over WebSockets to trigger 3D animations on the frontend. No actual LLM interaction logic exists.
- **Dependency Conflicts & OS Compatibility**: OS agnostic (standard web tech + basic python).
- **Security & Risks**: Insecure network exposure (`backend_server.py` hardcodes `host="0.0.0.0"` without authentication).
- **Recommendation**: **REJECT** the backend entirely. **DEFER** the 3D visualization concepts if SARATHI needs a 3D avatar frontend later.
