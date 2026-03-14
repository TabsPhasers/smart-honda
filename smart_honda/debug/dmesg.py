"""dmesg log parsing and filtering."""
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional
from datetime import timedelta


LEVEL_MAP = {
    "0": "EMERG",
    "1": "ALERT",
    "2": "CRIT",
    "3": "ERR",
    "4": "WARN",
    "5": "NOTICE",
    "6": "INFO",
    "7": "DEBUG",
}


@dataclass
class DmesgEntry:
    timestamp: Optional[float]
    level: str
    facility: str
    message: str
    raw: str

    @property
    def timedelta(self) -> Optional[timedelta]:
        if self.timestamp is not None:
            return timedelta(seconds=self.timestamp)
        return None


_ENTRY_RE = re.compile(
    r"^(?:<(?P<fac>\d+)>)?(?:\[?\s*(?P<ts>\d+\.\d+)\]?\s*)?(?P<msg>.*)$"
)
_LEVEL_RE = re.compile(r"^<(\d)(\d*)>")


def parse_raw(raw: str) -> DmesgEntry:
    level = "INFO"
    facility = "KERN"
    timestamp = None
    message = raw

    m = _LEVEL_RE.match(raw)
    if m:
        level = LEVEL_MAP.get(m.group(1), "INFO")
        raw = raw[m.end():]

    ts_m = re.match(r"^\[?\s*(\d+\.\d+)\]?\s*", raw)
    if ts_m:
        timestamp = float(ts_m.group(1))
        message = raw[ts_m.end():]
    else:
        message = raw

    return DmesgEntry(
        timestamp=timestamp,
        level=level,
        facility=facility,
        message=message.strip(),
        raw=raw.strip(),
    )


def read_dmesg(level: Optional[str] = None, since: Optional[float] = None) -> list[DmesgEntry]:
    """Read kernel ring buffer and return parsed entries."""
    result = subprocess.run(["dmesg", "--raw"], capture_output=True, text=True)
    entries = [parse_raw(line) for line in result.stdout.splitlines() if line.strip()]

    if level:
        level_upper = level.upper()
        level_order = list(LEVEL_MAP.values())
        max_idx = level_order.index(level_upper) if level_upper in level_order else len(level_order)
        entries = [e for e in entries if level_order.index(e.level) <= max_idx]

    if since is not None:
        entries = [e for e in entries if e.timestamp is not None and e.timestamp >= since]

    return entries


def search_dmesg(pattern: str, case_insensitive: bool = True) -> list[DmesgEntry]:
    """Search dmesg for entries matching a regex pattern."""
    flags = re.IGNORECASE if case_insensitive else 0
    rx = re.compile(pattern, flags)
    return [e for e in read_dmesg() if rx.search(e.message)]


def find_oops() -> list[DmesgEntry]:
    """Return entries that look like kernel oops/panics/BUGs."""
    keywords = r"(BUG:|Oops|kernel BUG|Call Trace|RIP:|general protection|segfault|Unable to handle)"
    return search_dmesg(keywords)


def find_module_messages(module_name: str) -> list[DmesgEntry]:
    return search_dmesg(re.escape(module_name))
