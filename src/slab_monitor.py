from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import time

import psutil  # for host memory info

@dataclass
class SlabSample:
    timestamp: float
    total_slab_kb: int
    per_cache_kb: Dict[str, int]
    host_mem_free_kb: int
    host_mem_available_kb: int

class SlabMonitor:
    def __init__(self, caches_of_interest: List[str]):
        self.caches_of_interest = set(caches_of_interest)
        self._last_sample: SlabSample | None = None

    @staticmethod
    def _read_proc_slabinfo() -> Dict[str, int]:
        """Return slab size in kB for all caches."""
        result = {}
        with Path("/proc/slabinfo").open() as f:
            # skip first two header lines
            next(f); next(f)
            for line in f:
                parts = line.split()
                if not parts:
                    continue
                name = parts[0]
                # format: name <active_objs> <num_objs> <objsize> <objperslab> <pagesperslab> ...
                try:
                    num_objs = int(parts[2])
                    obj_size = int(parts[3])
                    kb = (num_objs * obj_size) // 1024
                    result[name] = kb
                except (IndexError, ValueError):
                    continue
        return result

    @staticmethod
    def _read_host_meminfo() -> Dict[str, int]:
        vm = psutil.virtual_memory()
        return {
            "total_kb": vm.total // 1024,
            "available_kb": vm.available // 1024,
            "free_kb": vm.free // 1024,
        }

    def sample(self) -> SlabSample:
        slab_all = self._read_proc_slabinfo()
        host_mem = self._read_host_meminfo()
        per_cache = {
            name: slab_all.get(name, 0)
            for name in self.caches_of_interest
        }
        total_slab = sum(slab_all.values())
        sample = SlabSample(
            timestamp=time.time(),
            total_slab_kb=total_slab,
            per_cache_kb=per_cache,
            host_mem_free_kb=host_mem["free_kb"],
            host_mem_available_kb=host_mem["available_kb"],
        )
        self._last_sample = sample
        return sample
