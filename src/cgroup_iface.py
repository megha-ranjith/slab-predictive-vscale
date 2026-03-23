from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

@dataclass
class CgroupStats:
    timestamp: float
    name: str
    memory_current_bytes: int
    memory_high_bytes: int
    memory_max_bytes: int
    pgfault: int
    pgmajfault: int

class CgroupInterface:
    def __init__(self, root: Path, parent_slice: str):
        self.root = root
        self.parent_slice = parent_slice

    def cgroup_path(self, sub: str) -> Path:
        return self.root / self.parent_slice / sub

    @staticmethod
    def _read_int(path: Path) -> int:
        try:
            return int(path.read_text().strip())
        except FileNotFoundError:
            return 0

    def read_stats(self, sub: str, timestamp: float) -> Optional[CgroupStats]:
        cg = self.cgroup_path(sub)
        if not cg.exists():
            return None
        mem_current = self._read_int(cg / "memory.current")
        mem_high = self._read_int(cg / "memory.high")
        mem_max = self._read_int(cg / "memory.max")
        stat_path = cg / "memory.stat"
        pgfault = pgmajfault = 0
        if stat_path.exists():
            for line in stat_path.read_text().splitlines():
                k, v = line.split()
                if k == "pgfault":
                    pgfault = int(v)
                elif k == "pgmajfault":
                    pgmajfault = int(v)
        return CgroupStats(
            timestamp=timestamp,
            name=sub,
            memory_current_bytes=mem_current,
            memory_high_bytes=mem_high,
            memory_max_bytes=mem_max,
            pgfault=pgfault,
            pgmajfault=pgmajfault,
        )

    def set_memory_high(self, sub: str, bytes_val: int):
        cg = self.cgroup_path(sub)
        (cg / "memory.high").write_text(str(bytes_val))

    def set_memory_max(self, sub: str, bytes_val: int):
        cg = self.cgroup_path(sub)
        (cg / "memory.max").write_text(str(bytes_val))

    def add_pid(self, sub: str, pid: int):
        cg = self.cgroup_path(sub)
        (cg / "cgroup.procs").write_text(str(pid))
