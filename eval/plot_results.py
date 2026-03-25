import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1] / "data" / "logs"
PLOTS = Path(__file__).resolve().parents[1] / "data" / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

def load_data():
    # These files have no header row, so specify names explicitly
    slab = pd.read_csv(
        BASE / "slab_stats.csv",
        header=None,
        names=["timestamp", "total_slab_kb", "host_free_kb", "host_avail_kb", "per_cache_json"],
    )
    cg = pd.read_csv(
        BASE / "cgroup_stats.csv",
        header=None,
        names=["timestamp", "function", "cgroup", "mem_current", "mem_high", "mem_max", "pgfault", "pgmajfault"],
    )
    scaling = pd.read_csv(
        BASE / "scaling_events.csv",
        header=None,
        names=["timestamp", "function", "cgroup", "old_max_bytes", "new_max_bytes", "reason"],
    )

    # normalize time to start at 0
    t0 = min(slab["timestamp"].min(), cg["timestamp"].min())
    for df in (slab, cg, scaling):
        df["t_rel"] = df["timestamp"] - t0
    return slab, cg, scaling


def plot_memory_for_function(cg: pd.DataFrame, func_name: str):
    df = cg[cg["function"] == func_name].copy()
    if df.empty:
        return
    df = df.sort_values("t_rel")
    df["mem_cur_mb"] = df["mem_current"] / (1024 * 1024)
    df["mem_max_mb"] = df["mem_max"] / (1024 * 1024)

    plt.figure(figsize=(8, 4))
    plt.plot(df["t_rel"], df["mem_cur_mb"], label="memory.current (MiB)")
    plt.plot(df["t_rel"], df["mem_max_mb"], label="memory.max (MiB)", linestyle="--")
    plt.xlabel("Time (s)")
    plt.ylabel("Memory (MiB)")
    plt.title(f"Vertical scaling behavior for {func_name}")
    plt.legend()
    plt.tight_layout()
    out = PLOTS / f"mem_usage_{func_name}.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")

def plot_slab_and_host(slab: pd.DataFrame):
    # sort by time
    df = slab.sort_values("t_rel")

    # keep only the last 200 seconds so that the simulator run is visible
    t_max = df["t_rel"].max()
    df = df[df["t_rel"] >= t_max - 200]

    # convert to MiB
    df["slab_mib"] = df["total_slab_kb"] / 1024
    df["avail_mib"] = df["host_avail_kb"] / 1024

    # choose tight y‑limits around the actual values to make small changes visible
    slab_min, slab_max = df["slab_mib"].min(), df["slab_mib"].max()
    avail_min, avail_max = df["avail_mib"].min(), df["avail_mib"].max()

    plt.figure(figsize=(8, 4))
    plt.plot(df["t_rel"], df["slab_mib"], label="Total slab (MiB)")
    plt.plot(df["t_rel"], df["avail_mib"], label="Host available (MiB)")

    plt.xlabel("Time (s)")
    plt.ylabel("Memory (MiB)")
    plt.title("Host slab usage and available memory (last 200 s)")
    plt.legend()

    # set y‑limits with a small margin (±5 MiB) around the data range
    y_min = min(slab_min, avail_min) - 5
    y_max = max(slab_max, avail_max) + 5
    plt.ylim(y_min, y_max)

    plt.tight_layout()
    out = PLOTS / "slab_and_host_zoomed.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")


def plot_fault_rate(cg: pd.DataFrame, func_name: str):
    df = cg[cg["function"] == func_name].copy()
    if df.empty or len(df) < 2:
        return
    df = df.sort_values("t_rel")
    df["dt"] = df["t_rel"].diff()
    df["pgfault_delta"] = df["pgfault"].diff()
    df["fault_rate"] = df["pgfault_delta"] / df["dt"]

    plt.figure(figsize=(8, 4))
    plt.plot(df["t_rel"], df["fault_rate"], label="Minor fault rate (1/s)")
    plt.xlabel("Time (s)")
    plt.ylabel("Faults per second")
    plt.title(f"Minor page fault rate for {func_name}")
    plt.legend()
    plt.tight_layout()
    out = PLOTS / f"fault_rate_{func_name}.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")

def plot_intended_limits(scaling: pd.DataFrame, func_name: str):
    # Filter scaling events for this logical function name
    df = scaling[scaling["function"] == func_name].copy()
    if df.empty:
        return

    df = df.sort_values("t_rel")
    # Convert bytes to MiB for readability
    df["new_max_mb"] = df["new_max_bytes"] / (1024 * 1024)

    plt.figure(figsize=(8, 4))
    # Step plot shows piecewise-constant changes in memory.max
    plt.step(df["t_rel"], df["new_max_mb"], where="post",
             label="intended memory.max (MiB)")
    plt.xlabel("Time (s)")
    plt.ylabel("Memory (MiB)")
    plt.title(f"Predicted vertical scaling policy for {func_name}")
    plt.legend()
    plt.tight_layout()
    out = PLOTS / f"intended_limits_{func_name}.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved {out}")

def main():
    slab, cg, scaling = load_data()
    plot_slab_and_host(slab)
    for func in cg["function"].unique():
        plot_memory_for_function(cg, func)
        plot_fault_rate(cg, func)
        # NEW: plot intended memory.max over time
        plot_intended_limits(scaling, func)

if __name__ == "__main__":
    main()

