"""Kernel module management: build, load, unload, inspect."""
import os
from pathlib import Path
from typing import Optional
from ..utils.helpers import run_command, require_tool, current_kernel_version


class KernelModule:
    def __init__(self, source_dir: Path, name: Optional[str] = None):
        self.source_dir = source_dir
        self.name = name or source_dir.name

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, kernel_dir: Optional[str] = None) -> bool:
        """Compile the module against the running kernel (or kernel_dir)."""
        require_tool("make")
        kdir = kernel_dir or f"/lib/modules/{current_kernel_version()}/build"
        rc, _, err = run_command(
            ["make", f"KDIR={kdir}", "-C", kdir, f"M={self.source_dir}", "modules"],
            cwd=str(self.source_dir),
        )
        if rc != 0:
            raise RuntimeError(f"Module build failed:\n{err}")
        return True

    def clean(self, kernel_dir: Optional[str] = None):
        kdir = kernel_dir or f"/lib/modules/{current_kernel_version()}/build"
        run_command(
            ["make", f"KDIR={kdir}", "-C", kdir, f"M={self.source_dir}", "clean"],
            cwd=str(self.source_dir),
        )

    # ------------------------------------------------------------------
    # Load / Unload
    # ------------------------------------------------------------------

    def load(self, params: Optional[dict] = None) -> bool:
        """Load module with optional parameters (requires root)."""
        require_tool("insmod")
        ko_files = list(self.source_dir.glob("*.ko"))
        if not ko_files:
            raise FileNotFoundError(f"No .ko file found in {self.source_dir}")
        ko = ko_files[0]
        cmd = ["insmod", str(ko)]
        if params:
            cmd += [f"{k}={v}" for k, v in params.items()]
        rc, _, err = run_command(cmd)
        if rc != 0:
            raise RuntimeError(f"insmod failed:\n{err}")
        return True

    def unload(self) -> bool:
        """Unload module by name (requires root)."""
        require_tool("rmmod")
        rc, _, err = run_command(["rmmod", self.name])
        if rc != 0:
            raise RuntimeError(f"rmmod failed:\n{err}")
        return True

    def reload(self, params: Optional[dict] = None) -> bool:
        try:
            self.unload()
        except RuntimeError:
            pass
        return self.load(params)

    # ------------------------------------------------------------------
    # Inspect
    # ------------------------------------------------------------------

    def is_loaded(self) -> bool:
        rc, out, _ = run_command(["lsmod"])
        return any(
            line.split()[0] == self.name
            for line in out.splitlines()
            if line.split()
        )

    def info(self) -> dict:
        """Return modinfo output as a dict."""
        ko_files = list(self.source_dir.glob("*.ko"))
        if not ko_files:
            return {}
        rc, out, _ = run_command(["modinfo", str(ko_files[0])])
        result: dict = {}
        for line in out.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                result[key.strip()] = val.strip()
        return result

    @staticmethod
    def list_loaded() -> list[str]:
        rc, out, _ = run_command(["lsmod"])
        modules = []
        for line in out.splitlines()[1:]:
            parts = line.split()
            if parts:
                modules.append(parts[0])
        return modules

    @staticmethod
    def find_module(name: str) -> Optional[Path]:
        """Search /lib/modules for a .ko file by name."""
        kver = current_kernel_version()
        base = Path(f"/lib/modules/{kver}")
        for ko in base.rglob(f"{name}.ko*"):
            return ko
        return None

    def create_skeleton(self, author: str = "", description: str = "") -> None:
        """Write a minimal module .c and Makefile into source_dir."""
        self.source_dir.mkdir(parents=True, exist_ok=True)
        c_file = self.source_dir / f"{self.name}.c"
        makefile = self.source_dir / "Makefile"

        c_file.write_text(
            f"""\
// SPDX-License-Identifier: GPL-2.0
/*
 * {self.name} - {description or 'kernel module'}
 * Author: {author}
 */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("{author}");
MODULE_DESCRIPTION("{description or self.name}");
MODULE_VERSION("0.1");

static int __init {self.name}_init(void)
{{
    pr_info("{self.name}: module loaded\\n");
    return 0;
}}

static void __exit {self.name}_exit(void)
{{
    pr_info("{self.name}: module unloaded\\n");
}}

module_init({self.name}_init);
module_exit({self.name}_exit);
"""
        )

        makefile.write_text(
            f"""\
obj-m += {self.name}.o

KDIR ?= /lib/modules/$(shell uname -r)/build

all:
\t$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
\t$(MAKE) -C $(KDIR) M=$(PWD) clean
"""
        )
