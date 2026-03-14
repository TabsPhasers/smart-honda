"""Kernel compilation helpers."""
from pathlib import Path
from typing import Optional, Callable
from .config import KernelConfig
from ..utils.helpers import run_command, require_tool, nproc


class KernelCompiler:
    def __init__(self, source_dir: Path, build_dir: Optional[Path] = None):
        self.source_dir = source_dir
        self.build_dir = build_dir or source_dir
        self.config = KernelConfig(self.build_dir / ".config")

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def menuconfig(self):
        """Launch interactive ncurses config."""
        require_tool("make")
        rc, _, err = run_command(["make", "menuconfig"], cwd=str(self.source_dir))
        if rc != 0:
            raise RuntimeError(f"menuconfig failed:\n{err}")

    def olddefconfig(self):
        """Update config using defaults for new options."""
        require_tool("make")
        rc, _, err = run_command(["make", "olddefconfig"], cwd=str(self.source_dir))
        if rc != 0:
            raise RuntimeError(f"olddefconfig failed:\n{err}")

    def defconfig(self, arch: str = "x86_64"):
        """Generate default config for given arch."""
        require_tool("make")
        rc, _, err = run_command(
            ["make", f"ARCH={arch}", "defconfig"],
            cwd=str(self.source_dir),
        )
        if rc != 0:
            raise RuntimeError(f"defconfig failed:\n{err}")

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        jobs: Optional[int] = None,
        target: str = "",
        log_cb: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Build the kernel (or a sub-target). Returns True on success."""
        require_tool("make")
        j = jobs or nproc()
        cmd = ["make", f"-j{j}"]
        if target:
            cmd.append(target)
        rc, stdout, stderr = run_command(cmd, cwd=str(self.source_dir))
        if log_cb:
            for line in (stdout + stderr).splitlines():
                log_cb(line)
        return rc == 0

    def build_modules(self, jobs: Optional[int] = None) -> bool:
        return self.build(jobs=jobs, target="modules")

    def install_modules(self) -> bool:
        rc, _, _ = run_command(
            ["make", "modules_install"],
            cwd=str(self.source_dir),
        )
        return rc == 0

    def clean(self):
        run_command(["make", "clean"], cwd=str(self.source_dir))

    def mrproper(self):
        run_command(["make", "mrproper"], cwd=str(self.source_dir))

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    def kernel_version(self) -> str:
        rc, out, _ = run_command(["make", "kernelversion"], cwd=str(self.source_dir))
        return out.strip() if rc == 0 else "unknown"

    def list_targets(self) -> list[str]:
        rc, out, _ = run_command(["make", "help"], cwd=str(self.source_dir))
        if rc != 0:
            return []
        targets = []
        for line in out.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and " - " in line:
                targets.append(line.split(" - ")[0].strip())
        return targets
