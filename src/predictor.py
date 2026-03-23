from __future__ import annotations

from dataclasses import dataclass
from typing import Deque, Dict, List, Tuple
from collections import deque
import time

from .slab_monitor import SlabSample
from .cgroup_iface import CgroupStats

@dataclass
class Prediction:
    timestamp: float
    function_name: str
    will_be_under_pressure: bool
    confidence: float
    reason: str
    suggested_delta_bytes: int

class Predictor:
    def __init__(
        self,
        window: int,
        slab_growth_threshold_kb_per_sec: int,
        fault_rate_threshold: int,
    ):
        self.window = window
        self.slab_growth_thresh = slab_growth_threshold_kb_per_sec
        self.fault_rate_thresh = fault_rate_threshold
        self._slab_history: Deque[SlabSample] = deque(maxlen=window)
        self._cg_history: Dict[str, Deque[CgroupStats]] = {}

    def update_slab(self, sample: SlabSample):
        self._slab_history.append(sample)

    def update_cgroup(self, stats: CgroupStats):
        dq = self._cg_history.setdefault(stats.name, deque(maxlen=self.window))
        dq.append(stats)

    def _slab_growth_rate(self) -> Tuple[float, Dict[str, float]]:
        if len(self._slab_history) < 2:
            return 0.0, {}
        first = self._slab_history[0]
        last = self._slab_history[-1]
        dt = last.timestamp - first.timestamp
        if dt <= 0:
            return 0.0, {}
        total_rate = (last.total_slab_kb - first.total_slab_kb) / dt
        per_cache_rates = {}
        for name in last.per_cache_kb.keys():
            dv = last.per_cache_kb[name] - first.per_cache_kb.get(name, 0)
            per_cache_rates[name] = dv / dt
        return total_rate, per_cache_rates

    def _fault_rate(self, name: str) -> Tuple[float, float]:
        hist = self._cg_history.get(name)
        if not hist or len(hist) < 2:
            return 0.0, 0.0
        first = hist[0]
        last = hist[-1]
        dt = last.timestamp - first.timestamp
        if dt <= 0:
            return 0.0, 0.0
        minor = (last.pgfault - first.pgfault) / dt
        major = (last.pgmajfault - first.pgmajfault) / dt
        return minor, major

    def predict_for(self, func_name: str) -> Prediction:
        now = time.time()
        total_slab_rate, per_cache_rates = self._slab_growth_rate()
        minor_rate, major_rate = self._fault_rate(func_name)

        # heuristic scoring
        score = 0.0
        reason_parts: List[str] = []

        hot_caches = [
            (name, rate) for name, rate in per_cache_rates.items()
            if rate > self.slab_growth_thresh
        ]
        if hot_caches:
            score += 0.5
            top = ", ".join(f"{n}:{r:.1f}kB/s" for n, r in hot_caches[:3])
            reason_parts.append(f"hot slab caches: {top}")

        if minor_rate > self.fault_rate_thresh:
            score += 0.3
            reason_parts.append(f"high minor fault rate: {minor_rate:.1f}/s")

        if major_rate > 0.0:
            score += 0.2
            reason_parts.append(f"major faults present: {major_rate:.2f}/s")

        will = score >= 0.7
        delta = 0
        if will:
            # suggest one step up; actual step size is decided in controller
            delta = 1

        reason = "; ".join(reason_parts) if reason_parts else "no strong signals"
        return Prediction(
            timestamp=now,
            function_name=func_name,
            will_be_under_pressure=will,
            confidence=min(score, 1.0),
            reason=reason,
            suggested_delta_bytes=delta,  # controller will map this to bytes
        )
