import subprocess
import os
import shutil
from pathlib import Path
from typing import Optional


def run_command(cmd: list[str], cwd: Optional[str] = None, env: Optional[dict] = None) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def require_tool(name: str) -> str:
    """Return full path to a tool, raise if not found."""
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"Required tool not found: {name}")
    return path


def kernel_source_dir() -> Optional[Path]:
    """Best-guess location of kernel source tree."""
    candidates = [
        Path("/usr/src/linux"),
        Path("/usr/src") / f"linux-{os.uname().release}",
        Path(f"/lib/modules/{os.uname().release}/build"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def current_kernel_version() -> str:
    return os.uname().release


def nproc() -> int:
    return os.cpu_count() or 1
