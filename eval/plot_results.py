import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parents[1] / "data" / "logs"
PLOTS = Path(__file__).resolve().parents[1] / "data" / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

def load_data():
    slab = pd.read_csv(BASE / "slab_stats.csv")
    cg = pd.read_csv(BASE / "cgroup_stats.csv")
    scaling = pd.read_csv(BASE / "scaling_events.csv")
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
    df = slab.sort_values("t_rel")
    plt.figure(figsize=(8, 4))
    plt.plot(df["t_rel"], df["total_slab_kb"] / 1024, label="Total slab (MiB)")
    plt.plot(df["t_rel"], df["host_avail_kb"] / 1024, label="Host available (MiB)")
    plt.xlabel("Time (s)")
    plt.ylabel("Memory (MiB)")
    plt.title("Host slab usage and available memory over time")
    plt.legend()
    plt.tight_layout()
    out = PLOTS / "slab_and_host.png"
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

def main():
    slab, cg, scaling = load_data()
    plot_slab_and_host(slab)
    for func in cg["function"].unique():
        plot_memory_for_function(cg, func)
        plot_fault_rate(cg, func)

if __name__ == "__main__":
    main()
