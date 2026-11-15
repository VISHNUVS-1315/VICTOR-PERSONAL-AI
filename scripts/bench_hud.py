"""
Isolated idle benchmark for the VICTOR HUD
=========================================
Loads the real QML with no microphone, hotkeys, wake word or IPC, and reports
the process's own CPU and memory. Used to verify that the animation cost is low
without disturbing a running assistant.

Usage:
    python scripts/bench_hud.py --seconds 20              # HUD visible, idle
    python scripts/bench_hud.py --seconds 20 --hidden     # HUD hidden
    python scripts/bench_hud.py --seconds 20 --state listening
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("VICTOR_IPC_NAME", "VICTOR_HUD_BENCH")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qml.binding.removal.info=false")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psutil  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--hidden", action="store_true")
    parser.add_argument("--state", default="idle")
    parser.add_argument("--level", type=float, default=0.02)
    args = parser.parse_args()

    app = QGuiApplication(sys.argv)
    from src.ui.hud import VictorHudBackend

    backend = VictorHudBackend(qa_mode=True)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("victor", backend)
    engine.load(str(ROOT / "src" / "ui" / "qml" / "Hud.qml"))
    if not engine.rootObjects():
        print("HUD failed to load")
        return 1

    window = engine.rootObjects()[0]
    backend.attach_window(window)
    backend.debugSetState(args.state)
    backend.debugSetLevel(args.level)
    window.show()

    if args.hidden:
        QTimer.singleShot(1200, window.hide)

    proc = psutil.Process()
    proc.cpu_percent(None)
    samples = []
    peak = 0

    def sample() -> None:
        nonlocal peak
        rss = proc.memory_info().rss
        samples.append(rss)
        peak = max(peak, rss)

    timer = QTimer()
    timer.timeout.connect(sample)
    timer.start(500)
    QTimer.singleShot(int(args.seconds * 1000), app.quit)
    app.exec()

    cpu = proc.cpu_percent(None)
    cores = psutil.cpu_count() or 1
    print(f"mode: {'hidden' if args.hidden else 'visible'}, state={args.state}")
    print(f"ram_working_set_avg_mb: {sum(samples) / max(1, len(samples)) / 1_048_576:.0f}")
    print(f"ram_working_set_peak_mb: {peak / 1_048_576:.0f}")
    print(f"cpu_percent_of_all_cores: {cpu:.1f}%  ({cpu / cores:.1f}% of machine)")
    print(f"window_seconds: {args.seconds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
