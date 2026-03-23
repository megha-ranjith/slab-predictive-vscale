from __future__ import annotations

import os
import random
import time
from multiprocessing import Process
from pathlib import Path
from typing import Callable, Dict

import psutil

from .config import Config
from .cgroup_iface import CgroupInterface
from .logging_utils import setup_logger

def workload_mem_light(duration_sec: float):
    t_end = time.time() + duration_sec
    while time.time() < t_end:
        # allocate small buffers and free them
        buf = bytearray(1024 * 64)  # 64 KB
        for i in range(0, len(buf), 4096):
            buf[i] = 1
        time.sleep(0.01)

def workload_mem_heavy(duration_sec: float):
    t_end = time.time() + duration_sec
    blocks = []
    while time.time() < t_end:
        size_mb = random.choice([8, 16, 32])
        buf = bytearray(1024 * 1024 * size_mb)
        for i in range(0, len(buf), 4096):
            buf[i] = 1
        blocks.append(buf)
        # occasionally drop some blocks
        if len(blocks) > 8:
            blocks = blocks[-4:]
        time.sleep(0.05)

def workload_cpu_heavy_mem_heavy(duration_sec: float):
    t_end = time.time() + duration_sec
    buf = bytearray(1024 * 1024 * 64)  # 64 MB
    while time.time() < t_end:
        for i in range(0, len(buf), 4096):
            buf[i] = (buf[i] + 1) % 255

WORKLOADS: Dict[str, Callable[[float], None]] = {
    "func_cpu_light_mem_light": workload_mem_light,
    "func_cpu_light_mem_heavy": workload_mem_heavy,
    "func_cpu_heavy_mem_heavy": workload_cpu_heavy_mem_heavy,
}

class Simulator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.logger = setup_logger("simulator", cfg.logging_dir, to_stdout=True)
        self.cgroup = CgroupInterface(cfg.cgroup_root, cfg.functions_parent)

    def _run_func_instance(self, logical_name: str, duration: float):
        # attach this process to the right cgroup
        cg_name = self.cfg.functions[logical_name]
        self.cgroup.add_pid(cg_name, os.getpid())
        self.logger.info("Started %s in cgroup %s (pid=%d)", logical_name, cg_name, os.getpid())
        WORKLOADS[logical_name](duration)

    def run_bursty_pattern(self, total_rounds: int = 20):
        """Generate bursts of concurrent invocations for evaluation."""
        durations = {
            "func_cpu_light_mem_light": 0.5,
            "func_cpu_light_mem_heavy": 1.0,
            "func_cpu_heavy_mem_heavy": 2.0,
        }

        for r in range(total_rounds):
            procs = []
            for fname in self.cfg.functions.keys():
                # random 0-3 instances per function per round
                for _ in range(random.randint(0, 3)):
                    p = Process(target=self._run_func_instance, args=(fname, durations[fname]))
                    p.start()
                    procs.append(p)
            self.logger.info("Round %d: launched %d instances", r, len(procs))
            # stagger rounds
            time.sleep(0.5)
            # let processes finish
            for p in procs:
                p.join()

def main():
    cfg = Config("config.yaml")
    sim = Simulator(cfg)
    sim.run_bursty_pattern(total_rounds=30)

if __name__ == "__main__":
    main()
