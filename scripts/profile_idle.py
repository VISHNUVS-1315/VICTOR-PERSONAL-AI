"""
VICTOR Idle CPU & Memory Profiler
Isolates each subsystem to measure exact CPU% and RAM usage.
"""

import sys
import time
from pathlib import Path
import psutil

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

process = psutil.Process()

def measure(name: str, duration_sec: float = 3.0):
    # Warmup
    time.sleep(0.5)
    process.cpu_percent()
    t_start = time.time()
    time.sleep(duration_sec)
    cpu = process.cpu_percent()
    ram_mb = process.memory_info().rss / (1024 * 1024)
    print(f"[{name}] CPU: {cpu:.2f}% | RAM: {ram_mb:.1f} MB | Threads: {process.num_threads()}")
    return cpu, ram_mb

if __name__ == "__main__":
    print("--- 1. Baseline Python ---")
    measure("Baseline Python")

    print("\n--- 2. Telemetry Service alone ---")
    from src.services.telemetry_service import telemetry_service
    telemetry_service.start()
    measure("Telemetry Service (1.5s interval with nvidia-smi)")
    telemetry_service.stop()

    print("\n--- 3. Wake Word Service alone ---")
    from src.voice.wake_word import wake_word_service
    wake_word_service.start()
    measure("Wake Word Service (openwakeword streaming)")
    wake_word_service.stop()
