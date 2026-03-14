"""smart-honda CLI entry point."""
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

from .kernel.compiler import KernelCompiler
from .kernel.module import KernelModule
from .kernel.config import KernelConfig
from .debug.dmesg import read_dmesg, find_oops, find_module_messages, search_dmesg
from .debug.analyzer import analyze_file, decode_taint
from .utils.helpers import kernel_source_dir, current_kernel_version

console = Console()


@click.group()
@click.version_option()
def main():
    """smart-honda: Linux kernel debugging assistant."""


# ======================================================================
# kernel sub-group
# ======================================================================

@main.group()
def kernel():
    """Kernel compilation commands."""


@kernel.command("build")
@click.option("--source", "-s", default=None, help="Kernel source directory")
@click.option("--jobs", "-j", default=None, type=int, help="Parallel jobs")
@click.option("--target", "-t", default="", help="Make target (e.g. bzImage)")
def kernel_build(source, jobs, target):
    """Build the kernel."""
    src = Path(source) if source else kernel_source_dir()
    if src is None:
        console.print("[red]Cannot find kernel source. Use --source.[/red]")
        sys.exit(1)
    compiler = KernelCompiler(src)
    console.print(f"Building kernel in [cyan]{src}[/cyan] ...")

    def log(line):
        if "error:" in line.lower():
            console.print(f"[red]{line}[/red]")
        elif "warning:" in line.lower():
            console.print(f"[yellow]{line}[/yellow]")

    ok = compiler.build(jobs=jobs, target=target, log_cb=log)
    if ok:
        console.print("[green]Build succeeded.[/green]")
    else:
        console.print("[red]Build failed.[/red]")
        sys.exit(1)


@kernel.command("version")
@click.option("--source", "-s", default=None)
def kernel_version(source):
    """Print kernel version from source tree or running kernel."""
    if source:
        c = KernelCompiler(Path(source))
        ver = c.kernel_version()
    else:
        ver = current_kernel_version()
    console.print(ver)


@kernel.command("config-get")
@click.argument("option")
@click.option("--config", default=None, help="Path to .config file")
def config_get(option, config):
    """Get a kernel config option value."""
    cfg_path = Path(config) if config else (kernel_source_dir() or Path(".")) / ".config"
    cfg = KernelConfig(cfg_path)
    val = cfg.get(option)
    if val is None:
        console.print(f"[yellow]CONFIG_{option} is not set[/yellow]")
    else:
        console.print(f"CONFIG_{option}={val}")


@kernel.command("config-set")
@click.argument("option")
@click.argument("value")
@click.option("--config", default=None)
def config_set(option, value, config):
    """Set a kernel config option."""
    cfg_path = Path(config) if config else (kernel_source_dir() or Path(".")) / ".config"
    cfg = KernelConfig(cfg_path)
    cfg.set(option, value)
    cfg.save()
    console.print(f"[green]Set CONFIG_{option}={value}[/green]")


@kernel.command("config-search")
@click.argument("keyword")
@click.option("--config", default=None)
def config_search(keyword, config):
    """Search kernel config options by keyword."""
    cfg_path = Path(config) if config else (kernel_source_dir() or Path(".")) / ".config"
    cfg = KernelConfig(cfg_path)
    results = cfg.search(keyword)
    if not results:
        console.print(f"[yellow]No config options found matching '{keyword}'[/yellow]")
        return
    table = Table(title=f"Config options matching '{keyword}'")
    table.add_column("Option", style="cyan")
    table.add_column("Value", style="green")
    for opt, val in results:
        table.add_row(opt, val)
    console.print(table)


# ======================================================================
# module sub-group
# ======================================================================

@main.group()
def module():
    """Kernel module commands."""


@module.command("new")
@click.argument("name")
@click.option("--dir", "-d", default=None, help="Output directory")
@click.option("--author", default="", help="Module author")
@click.option("--desc", default="", help="Module description")
def module_new(name, dir, author, desc):
    """Create a new kernel module skeleton."""
    out_dir = Path(dir) if dir else Path.cwd() / name
    mod = KernelModule(out_dir, name)
    mod.create_skeleton(author=author, description=desc)
    console.print(f"[green]Created module skeleton in {out_dir}[/green]")
    console.print(f"  {out_dir}/{name}.c")
    console.print(f"  {out_dir}/Makefile")


@module.command("build")
@click.argument("path", default=".")
@click.option("--kdir", default=None, help="Kernel build directory")
def module_build(path, kdir):
    """Build a kernel module."""
    src = Path(path).resolve()
    mod = KernelModule(src)
    console.print(f"Building module in [cyan]{src}[/cyan] ...")
    try:
        mod.build(kernel_dir=kdir)
        console.print("[green]Module build succeeded.[/green]")
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)


@module.command("load")
@click.argument("path", default=".")
@click.argument("params", nargs=-1)
def module_load(path, params):
    """Load a kernel module (requires root)."""
    src = Path(path).resolve()
    mod = KernelModule(src)
    param_dict = {}
    for p in params:
        k, _, v = p.partition("=")
        param_dict[k] = v
    try:
        mod.load(param_dict or None)
        console.print(f"[green]Module {mod.name} loaded.[/green]")
    except (RuntimeError, FileNotFoundError) as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)


@module.command("unload")
@click.argument("name")
def module_unload(name):
    """Unload a kernel module by name (requires root)."""
    mod = KernelModule(Path("."), name)
    try:
        mod.unload()
        console.print(f"[green]Module {name} unloaded.[/green]")
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)


@module.command("list")
def module_list():
    """List currently loaded kernel modules."""
    modules = KernelModule.list_loaded()
    table = Table(title="Loaded kernel modules")
    table.add_column("Module", style="cyan")
    for m in modules:
        table.add_row(m)
    console.print(table)


@module.command("info")
@click.argument("path", default=".")
def module_info(path):
    """Show modinfo for a module."""
    src = Path(path).resolve()
    mod = KernelModule(src)
    info = mod.info()
    if not info:
        console.print("[yellow]No .ko file found or modinfo unavailable.[/yellow]")
        return
    table = Table(title=f"Module info: {src.name}")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    for k, v in info.items():
        table.add_row(k, v)
    console.print(table)


# ======================================================================
# debug sub-group
# ======================================================================

@main.group()
def debug():
    """Kernel debugging commands."""


@debug.command("dmesg")
@click.option("--level", "-l", default=None, help="Max log level (ERR, WARN, INFO, ...)")
@click.option("--grep", "-g", default=None, help="Filter by pattern")
@click.option("--module", "-m", default=None, help="Filter by module name")
@click.option("--tail", "-n", default=50, type=int, help="Show last N entries")
def dmesg_cmd(level, grep, module, tail):
    """Show kernel ring buffer messages."""
    if module:
        entries = find_module_messages(module)
    elif grep:
        entries = search_dmesg(grep)
    else:
        entries = read_dmesg(level=level)

    entries = entries[-tail:]

    level_colors = {
        "EMERG": "bold red",
        "ALERT": "bold red",
        "CRIT": "bold red",
        "ERR": "red",
        "WARN": "yellow",
        "NOTICE": "cyan",
        "INFO": "white",
        "DEBUG": "dim white",
    }

    for e in entries:
        ts = f"[{e.timestamp:>10.6f}]" if e.timestamp is not None else ""
        color = level_colors.get(e.level, "white")
        console.print(f"[dim]{ts}[/dim] [{color}]{e.level:<6}[/{color}] {e.message}")


@debug.command("oops")
def oops_cmd():
    """Find and display kernel oops/BUG entries from dmesg."""
    entries = find_oops()
    if not entries:
        console.print("[green]No oops/BUG entries found in dmesg.[/green]")
        return
    console.print(f"[red]Found {len(entries)} suspicious entries:[/red]\n")
    for e in entries:
        ts = f"[{e.timestamp:.6f}]" if e.timestamp else ""
        console.print(f"[red]{ts} {e.message}[/red]")


@debug.command("analyze")
@click.argument("file", type=click.Path(exists=True))
def analyze_cmd(file):
    """Analyze a kernel oops/crash log file."""
    report = analyze_file(Path(file))
    console.print(Panel(report.summary(), title="Crash Analysis", border_style="red"))
    if report.tainted:
        reasons = decode_taint(report.tainted)
        if reasons:
            console.print("\n[yellow]Taint reasons:[/yellow]")
            for r in reasons:
                console.print(f"  - {r}")


if __name__ == "__main__":
    main()
