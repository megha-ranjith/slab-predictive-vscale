from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Dict

from config import Config
from logging_utils import setup_logger
from slab_monitor import SlabMonitor
from cgroup_iface import CgroupInterface
from predictor import Predictor, Prediction


class Controller:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        log_dir = cfg.logging_dir
        self.logger = setup_logger("slab_vscale", log_dir, to_stdout=cfg._cfg["logging"]["enable_stdout"])

        self.slab_monitor = SlabMonitor(cfg.slab_caches)
        self.cgroup = CgroupInterface(cfg.cgroup_root, cfg.functions_parent)
        pred_cfg = cfg.prediction
        self.predictor = Predictor(
            window=cfg._cfg["prediction_window"],
            slab_growth_threshold_kb_per_sec=pred_cfg["slab_growth_threshold_kb_per_sec"],
            fault_rate_threshold=pred_cfg["cgroup_fault_rate_threshold"],
        )

        self.func_name_to_cg = cfg.functions  # logical → cgroup name
        self.vertical_cfg = cfg.vertical

        # CSV log paths
        base = cfg.logging_dir
        base.mkdir(parents=True, exist_ok=True)
        self.scaling_log = base / "scaling_events.csv"
        self.slab_log = base / "slab_stats.csv"
        self.cg_log = base / "cgroup_stats.csv"

        self._init_csv_files()

    def _init_csv_files(self):
        if not self.scaling_log.exists():
            with self.scaling_log.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "function", "cgroup", "old_max_bytes", "new_max_bytes", "reason"])
        if not self.slab_log.exists():
            with self.slab_log.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "total_slab_kb", "host_free_kb", "host_avail_kb", "per_cache_json"])
        if not self.cg_log.exists():
            with self.cg_log.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "function", "cgroup", "mem_current", "mem_high", "mem_max", "pgfault", "pgmajfault"])

    def _log_slab(self, sample):
        import json
        with self.slab_log.open("a", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                sample.timestamp,
                sample.total_slab_kb,
                sample.host_mem_free_kb,
                sample.host_mem_available_kb,
                json.dumps(sample.per_cache_kb),
            ])

    def _log_cgroup_stats(self, func_logical: str, cg_name: str, stats):
        with self.cg_log.open("a", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                stats.timestamp,
                func_logical,
                cg_name,
                stats.memory_current_bytes,
                stats.memory_high_bytes,
                stats.memory_max_bytes,
                stats.pgfault,
                stats.pgmajfault,
            ])

    def _log_scaling(self, func_logical: str, cg_name: str, old_max: int, new_max: int, reason: str):
        with self.scaling_log.open("a", newline="") as f:
            w = csv.writer(f)
            w.writerow([time.time(), func_logical, cg_name, old_max, new_max, reason])

    def _apply_vertical_scale(self, func_logical: str, cg_name: str, pred: Prediction, stats) -> None:
        min_mb = self.vertical_cfg["min_limit_mb"]
        max_mb = self.vertical_cfg["max_limit_mb"]
        step_up_mb = self.vertical_cfg["step_up_mb"]
        step_down_mb = self.vertical_cfg["step_down_mb"]

        old_max = stats.memory_max_bytes if stats.memory_max_bytes > 0 else max_mb * 1024 * 1024

        # Simple policy: if prediction is positive → step up, else consider step down if utilization is low
        if pred.will_be_under_pressure:
            target_mb = min(max_mb, old_max // (1024 * 1024) + step_up_mb)
            reason = f"predictive scale-up ({pred.reason})"
        else:
            # utilization-based scale-down: if current < 50% of max, reduce a bit
            cur_mb = stats.memory_current_bytes / (1024 * 1024)
            old_mb = old_max / (1024 * 1024)
            if old_mb <= min_mb or cur_mb / max(old_mb, 1) > 0.5:
                return
            target_mb = max(min_mb, old_mb - step_down_mb)
            reason = "conservative scale-down (low utilization)"

        new_max = target_mb * 1024 * 1024
        if new_max == old_max:
            return

        self.cgroup.set_memory_max(cg_name, new_max)
        self.logger.info(
            "Scaled %s (%s): %.0f MiB → %.0f MiB (%s)",
            func_logical, cg_name, old_max / (1024 * 1024), target_mb, reason
        )
        self._log_scaling(func_logical, cg_name, old_max, new_max, reason)

    def run(self):
        self.logger.info("Starting Slab-Predictive V-Scale controller")
        interval = self.cfg.sampling_interval_sec
        while True:
            start_ts = time.time()
            slab_sample = self.slab_monitor.sample()
            self.predictor.update_slab(slab_sample)
            self._log_slab(slab_sample)

            for func_logical, cg_name in self.func_name_to_cg.items():
                stats = self.cgroup.read_stats(cg_name, timestamp=slab_sample.timestamp)
                if stats is None:
                    continue
                self.predictor.update_cgroup(stats)
                self._log_cgroup_stats(func_logical, cg_name, stats)
                pred = self.predictor.predict_for(cg_name)
                self._apply_vertical_scale(func_logical, cg_name, pred, stats)

            elapsed = time.time() - start_ts
            sleep_for = max(0.0, interval - elapsed)
            time.sleep(sleep_for)
