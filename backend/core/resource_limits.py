"""Small dependency-free helpers for bounded free-tier resource usage."""

from __future__ import annotations

import os
from pathlib import Path


def positive_int_env(name: str, default: int, *, maximum: int) -> int:
    """Read a positive integer without allowing an unsafe accidental value."""
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    return min(value, maximum)


def process_memory_snapshot() -> dict[str, float | None]:
    """Return current process and cgroup memory without adding psutil."""
    values: dict[str, float | None] = {
        "rss_mib": None,
        "peak_rss_mib": None,
        "cgroup_used_mib": None,
        "cgroup_limit_mib": None,
        "cgroup_headroom_mib": None,
    }
    try:
        status = Path("/proc/self/status").read_text(encoding="utf-8")
        fields = {
            line.split(":", 1)[0]: line.split(":", 1)[1].strip()
            for line in status.splitlines()
            if ":" in line
        }
        for source, destination in (("VmRSS", "rss_mib"), ("VmHWM", "peak_rss_mib")):
            amount = fields.get(source, "").split(maxsplit=1)
            if amount:
                values[destination] = round(int(amount[0]) / 1024, 2)
    except (OSError, ValueError):
        pass

    try:
        used = int(Path("/sys/fs/cgroup/memory.current").read_text(encoding="utf-8").strip())
        raw_limit = Path("/sys/fs/cgroup/memory.max").read_text(encoding="utf-8").strip()
        limit = None if raw_limit == "max" else int(raw_limit)
        values["cgroup_used_mib"] = round(used / (1024 * 1024), 2)
        if limit is not None:
            values["cgroup_limit_mib"] = round(limit / (1024 * 1024), 2)
            values["cgroup_headroom_mib"] = round((limit - used) / (1024 * 1024), 2)
    except (OSError, ValueError):
        pass
    return values
