from __future__ import annotations

import pytest

from tools.terminal.safe_command import SafeCommandTool, _Args


@pytest.mark.asyncio
async def test_unknown_command_rejected():
    t = SafeCommandTool()
    r = await t.execute(_Args(command="rm", args=["-rf", "/"]))
    assert not r.success
    assert "allowlist" in (r.error or "")


@pytest.mark.asyncio
async def test_git_push_rejected():
    t = SafeCommandTool()
    r = await t.execute(_Args(command="git", args=["push"]))
    assert not r.success


@pytest.mark.asyncio
async def test_shell_metacharacter_rejected():
    t = SafeCommandTool()
    r = await t.execute(_Args(command="echo", args=["hi; rm -rf /"]))
    assert not r.success


@pytest.mark.asyncio
async def test_python_version_runs():
    t = SafeCommandTool()
    r = await t.execute(_Args(command="python", args=["--version"]))
    # Allow either success or "binary not found" on exotic environments.
    if not r.success:
        assert "not found" in (r.error or "").lower()
    else:
        assert "python" in r.output["stdout"].lower()
