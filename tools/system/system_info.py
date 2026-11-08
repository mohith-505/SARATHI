"""System information tool: OS, CPU, RAM, GPU, disk, top processes."""

from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Any

import psutil
from pydantic import BaseModel

from core.logging.logger import get_logger
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult

log = get_logger("tools.system_info")


class _Args(BaseModel):
    include_gpu: bool = True
    include_disk: bool = True
    include_processes: bool = False


def _try_nvidia_smi() -> list[dict[str, Any]]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    try:
        out = subprocess.run(  # noqa: S603, ASYNC221
            [
                exe,
                "--query-gpu=name,memory.total,memory.used,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        log.debug("nvidia-smi failed: %s", e)
        return []
    gpus: list[dict[str, Any]] = []
    for line in out.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4:
            gpus.append(
                {
                    "name": parts[0],
                    "vram_total_mb": int(parts[1]) if parts[1].isdigit() else None,
                    "vram_used_mb": int(parts[2]) if parts[2].isdigit() else None,
                    "driver_version": parts[3],
                }
            )
    return gpus


class SystemInfoTool(Tool):
    name = "system_information"
    description = (
        "Return basic system info: OS, CPU, RAM, and optionally "
        "GPU, disk usage, and top processes by memory."
    )
    permission_level = PermissionLevel.T0
    input_schema = _Args

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        vm = psutil.virtual_memory()
        info: dict[str, Any] = {
            "os": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
            },
            "python": platform.python_version(),
            "cpu": {
                "model": platform.processor() or "unknown",
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
            },
            "memory": {
                "total_mb": round(vm.total / (1024 * 1024), 1),
                "available_mb": round(vm.available / (1024 * 1024), 1),
                "percent_used": vm.percent,
            },
        }

        if args.include_gpu:
            info["gpu"] = _try_nvidia_smi()

        if args.include_disk:
            disks = []
            for part in psutil.disk_partitions(all=False):
                if not part.fstype or not part.mountpoint:
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                except OSError:
                    continue
                disks.append(
                    {
                        "mountpoint": part.mountpoint,
                        "total_gb": round(usage.total / (1024**3), 1),
                        "used_gb": round(usage.used / (1024**3), 1),
                        "percent": usage.percent,
                    }
                )
            info["disk"] = disks

        if args.include_processes:
            rows: list[dict[str, Any]] = []
            for p in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    meminfo = p.info.get("memory_info")
                    rss = meminfo.rss if meminfo is not None else 0
                    rows.append(
                        {
                            "pid": p.info["pid"],
                            "name": p.info["name"],
                            "rss_mb": round(rss / (1024 * 1024), 1),
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            rows.sort(key=lambda r: r["rss_mb"], reverse=True)
            info["top_processes_by_memory"] = rows[:10]

        return ToolResult(success=True, output=info, verified=True)
