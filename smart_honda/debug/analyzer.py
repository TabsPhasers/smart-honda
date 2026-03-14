"""Crash log and oops analyzer."""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class OopsReport:
    raw: str
    rip: Optional[str] = None
    call_trace: list[str] = field(default_factory=list)
    bug_type: Optional[str] = None
    module: Optional[str] = None
    tainted: Optional[str] = None
    kernel_version: Optional[str] = None

    def summary(self) -> str:
        lines = []
        if self.bug_type:
            lines.append(f"Bug type   : {self.bug_type}")
        if self.kernel_version:
            lines.append(f"Kernel     : {self.kernel_version}")
        if self.tainted:
            lines.append(f"Tainted    : {self.tainted}")
        if self.rip:
            lines.append(f"RIP        : {self.rip}")
        if self.module:
            lines.append(f"Module     : {self.module}")
        if self.call_trace:
            lines.append("Call Trace :")
            for frame in self.call_trace:
                lines.append(f"  {frame}")
        return "\n".join(lines)


def parse_oops(text: str) -> OopsReport:
    report = OopsReport(raw=text)

    m = re.search(r"(BUG: [^\n]+|Oops[^\n]*|kernel BUG at [^\n]+)", text)
    if m:
        report.bug_type = m.group(1).strip()

    m = re.search(r"RIP:\s*(\S+[^\n]+)", text)
    if m:
        report.rip = m.group(1).strip()

    m = re.search(r"Tainted:\s*([^\n]+)", text)
    if m:
        report.tainted = m.group(1).strip()

    m = re.search(r"Linux version ([^\s]+)", text)
    if m:
        report.kernel_version = m.group(1)

    # Collect call trace frames.
    # Supports both plain kernel format ("  func+0x.../0x...") and
    # dmesg format with timestamps ("[  123.456]  func+0x.../0x...").
    _TS_PREFIX = re.compile(r"^\[?\s*\d+\.\d+\]?\s*")
    in_trace = False
    for line in text.splitlines():
        if "Call Trace" in line:
            in_trace = True
            continue
        if in_trace:
            stripped = _TS_PREFIX.sub("", line)  # remove optional timestamp
            frame_m = re.match(r"\s*\[?<?(\S+\+0x[0-9a-f]+/0x[0-9a-f]+)>?\]?", stripped)
            if frame_m:
                report.call_trace.append(frame_m.group(1))
            elif stripped.strip() and not stripped.startswith(" ") and not re.match(r"^\s*<", stripped):
                in_trace = False

    # Detect offending module from taint or RIP
    if report.rip:
        mod_m = re.search(r"\[([^\]]+)\]", report.rip)
        if mod_m:
            report.module = mod_m.group(1)

    return report


def analyze_file(path: Path) -> OopsReport:
    return parse_oops(path.read_text())


def decode_taint(taint_flags: str) -> list[str]:
    """Decode kernel taint flags string into human-readable reasons."""
    flag_map = {
        "G": "proprietary module loaded",
        "P": "module with non-GPL license",
        "F": "module force-loaded",
        "S": "SMP with non-SMP kernel",
        "R": "module force-unloaded",
        "M": "machine check error",
        "B": "bad page referenced",
        "U": "user-space tainted",
        "D": "kernel died (oops/BUG)",
        "A": "ACPI table overridden",
        "W": "taint on warning",
        "C": "staging driver loaded",
        "I": "ACPI workaround",
        "O": "out-of-tree module",
        "E": "unsigned module",
        "L": "soft lockup",
        "K": "kernel live patch",
    }
    return [flag_map[c] for c in taint_flags if c in flag_map]
