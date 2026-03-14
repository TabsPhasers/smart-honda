"""Kernel .config management helpers."""
import re
from pathlib import Path
from typing import Optional


class KernelConfig:
    """Read and manipulate a Linux kernel .config file."""

    def __init__(self, path: Path):
        self.path = path
        self._lines: list[str] = []
        self._load()

    def _load(self):
        if self.path.exists():
            self._lines = self.path.read_text().splitlines(keepends=True)
        else:
            self._lines = []

    def get(self, option: str) -> Optional[str]:
        """Return the value of CONFIG_<option>, or None if not set."""
        pattern = re.compile(rf"^CONFIG_{re.escape(option)}=(.+)$")
        for line in self._lines:
            m = pattern.match(line)
            if m:
                return m.group(1).strip('"')
        return None

    def set(self, option: str, value: str):
        """Set CONFIG_<option>=value, add if missing."""
        key = f"CONFIG_{option}"
        new_line = f"{key}={value}\n"
        not_set_pattern = re.compile(rf"^# {re.escape(key)} is not set")
        existing_pattern = re.compile(rf"^{re.escape(key)}=")

        for i, line in enumerate(self._lines):
            if existing_pattern.match(line) or not_set_pattern.match(line):
                self._lines[i] = new_line
                return
        self._lines.append(new_line)

    def disable(self, option: str):
        """Disable CONFIG_<option>."""
        key = f"CONFIG_{option}"
        pattern = re.compile(rf"^{re.escape(key)}=")
        for i, line in enumerate(self._lines):
            if pattern.match(line):
                self._lines[i] = f"# {key} is not set\n"
                return
        self._lines.append(f"# {key} is not set\n")

    def save(self):
        self.path.write_text("".join(self._lines))

    def search(self, keyword: str) -> list[tuple[str, str]]:
        """Return [(option, value)] for all options matching keyword."""
        results = []
        pattern = re.compile(rf"^CONFIG_[^\s=]*{re.escape(keyword.upper())}[^\s=]*=(.+)$", re.IGNORECASE)
        for line in self._lines:
            m = pattern.match(line)
            if m:
                option = line.split("=")[0]
                results.append((option, m.group(1)))
        return results
