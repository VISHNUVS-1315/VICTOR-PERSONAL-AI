"""
Measure VICTOR's real resource use
==================================
Samples the VICTOR process (working set, private bytes, CPU time) and the GPU
(memory, utilisation) over a window and prints a compact summary.

Usage:
    python scripts/measure_resources.py --label "HUD idle" --seconds 20
    python scripts/measure_resources.py --label "Classic UI" --seconds 20 --classic
    python scripts/measure_resources.py --label "HUD listening" --seconds 15 --hotkey
"""

from __future__ import annotations

import argparse
import ctypes
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]


def find_victor_pids() -> list[int]:
    pids = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info["name"] or "").lower()
            if name not in ("python.exe", "pythonw.exe"):
                continue
            cmd = " ".join(proc.info["cmdline"] or [])
            if "run_victor" in cmd or "src.ui.hud" in cmd or "main_legacy" in cmd:
                pids.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids


def send_hotkey() -> None:
    user32 = ctypes.windll.user32
    KEYUP = 0x0002
    user32.keybd_event(0x11, 0, 0, 0)
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x56, 0, 0, 0)
    time.sleep(0.06)
    user32.keybd_event(0x56, 0, KEYUP, 0)
    user32.keybd_event(0x12, 0, KEYUP, 0)
    user32.keybd_event(0x11, 0, KEYUP, 0)


def gpu_snapshot() -> str:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu,utilization.memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return "n/a"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--hotkey", action="store_true", help="press Ctrl+Alt+V first")
    args = parser.parse_args()

    pids = find_victor_pids()
    if not pids:
        print("No running VICTOR process found.")
        return 1

    procs = [psutil.Process(pid) for pid in pids]
    for p in procs:
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass

    print(f"label: {args.label}")
    print(f"pids: {[p.pid for p in procs]}")
    print(f"gpu_before: {gpu_snapshot()}")

    if args.hotkey:
        send_hotkey()
        time.sleep(2.0)

    start = time.perf_counter()
    peak_ws = 0
    peak_priv = 0
    samples = []
    while time.perf_counter() - start < args.seconds:
        ws = priv = 0
        for p in procs:
            try:
                with p.oneshot():
                    ws += p.memory_info().rss
                    priv += p.memory_info().private
            except psutil.Error:
                pass
        peak_ws = max(peak_ws, ws)
        peak_priv = max(peak_priv, priv)
        samples.append(ws)
        time.sleep(0.5)
    elapsed = time.perf_counter() - start

    total_cpu = 0.0
    for p in procs:
        try:
            total_cpu += p.cpu_percent(None)
        except psutil.Error:
            pass
    cores = psutil.cpu_count() or 1

    print(f"ram_working_set_peak_mb: {peak_ws / 1_048_576:.0f}")
    print(f"ram_private_peak_mb: {peak_priv / 1_048_576:.0f}")
    print(f"ram_working_set_avg_mb: {sum(samples) / len(samples) / 1_048_576:.0f}")
    print(f"cpu_percent_of_all_cores: {total_cpu:.1f}%  ({total_cpu / cores:.1f}% of machine)")
    print(f"gpu_after: {gpu_snapshot()}")
    print(f"window_seconds: {elapsed:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
