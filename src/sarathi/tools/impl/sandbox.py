import os
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from sarathi.core.types import Context, Tier, Trust
from sarathi.core.config import config

class PythonExecArgs(BaseModel):
    code: str = Field(..., description="Python code to execute")

class PythonExecTool:
    name = "python_exec"
    description = "Execute python code inside a secure, network-less sandbox"
    tier = Tier.T2
    output_trust = Trust.TRUSTED
    schema = PythonExecArgs

    async def run(self, args: PythonExecArgs, ctx: Context) -> str:
        # Create a temporary script file in the workspace
        workspace = Path(config.paths.workspace).expanduser().resolve()
        script_path = workspace / ".tmp_script.py"
        script_path.write_text(args.code, encoding="utf-8")
        
        # Windows path to unix path if using Docker Desktop with WSL backend.
        # But for Windows native Docker, we can mount directly using windows paths.
        
        # We'll use docker run --rm --network none
        cmd = [
            "docker", "run", "--rm", 
            "--network", "none",
            "--memory", "2g",
            "--cpus", "2",
            "-v", f"{workspace}:/workspace",
            "-w", "/workspace",
            "python:3.11-slim",
            "python3", ".tmp_script.py"
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = res.stdout
            if res.stderr:
                output += "\n[STDERR]\n" + res.stderr
            return output or "[No output]"
        except subprocess.TimeoutExpired:
            return "ERROR: Execution timed out after 60s"
        finally:
            if script_path.exists():
                script_path.unlink()

class RunShellArgs(BaseModel):
    command: str = Field(..., description="Shell command to run")

class RunShellTool:
    name = "run_shell"
    description = "Run a shell command in the sandbox"
    tier = Tier.T2
    output_trust = Trust.TRUSTED
    schema = RunShellArgs

    def __init__(self, allow_binaries: list[str], deny_patterns: list[str]):
        self.allow_binaries = allow_binaries
        self.deny_patterns = deny_patterns

    async def run(self, args: RunShellArgs, ctx: Context) -> str:
        cmd_str = args.command.strip()
        
        # Check denylist
        for pattern in self.deny_patterns:
            if pattern in cmd_str:
                return f"DENIED: command contains denied pattern {pattern!r}"
                
        # Basic binary allowlist check
        base_bin = cmd_str.split()[0] if cmd_str else ""
        if base_bin not in self.allow_binaries:
            return f"DENIED: binary {base_bin!r} is not on the allowlist"

        workspace = Path(config.paths.workspace).expanduser().resolve()
        
        cmd = [
            "docker", "run", "--rm", 
            "--network", "none",
            "--memory", "2g",
            "--cpus", "2",
            "-v", f"{workspace}:/workspace",
            "-w", "/workspace",
            "ubuntu:22.04",
            "sh", "-c", cmd_str
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = res.stdout
            if res.stderr:
                output += "\n[STDERR]\n" + res.stderr
            return output or "[No output]"
        except subprocess.TimeoutExpired:
            return "ERROR: Execution timed out after 60s"
