"""
HUD render harness
==================
Loads the real HUD and captures one PNG per animation state so the interface can
be reviewed without speaking to it. Used for visual QA and regression checks.

Rendering is done by QML itself (grabToImage), which is reliable regardless of
what the desktop compositor is doing.

Usage:
    python run_victor.py --capture out_dir
"""

from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QTimer

STEPS = [
    # (state, audio level, filename, sample messages)
    ("idle", 0.02, "01_idle.png", []),
    ("listening", 0.55, "02_listening.png", [
        ("YOU", "Open Visual Studio Code and check my CPU temperature."),
    ]),
    ("thinking", 0.10, "03_thinking.png", []),
    ("speaking", 0.62, "04_speaking.png", [
        ("VICTOR", "CPU is at 46 degrees, GPU is idle. Visual Studio Code is open."),
    ]),
]


def run_capture(app, window, backend, out_dir: str, _state: str = "") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    window.show()

    queue = list(STEPS)

    # Hard safety net: never leave a stray HUD process behind.
    QTimer.singleShot(30_000, backend.quitApp)

    def grab(name: str, state: str) -> None:
        try:
            path = out / name
            if path.exists():
                path.unlink()
            window.setProperty("capturePath", "")          # reset so the binding fires
            window.setProperty("capturePath", str(path))
            print(
                f"[capture] requested {name} state={state} backend={backend.systemState}",
                flush=True,
            )
        except Exception:
            traceback.print_exc()

    def step() -> None:
        if not queue:
            QTimer.singleShot(900, backend.quitApp)
            return
        state, level, name, messages = queue.pop(0)
        backend.debugSetState(state)
        backend.debugSetLevel(level)
        for role, text in messages:
            backend.debugAddMessage(role, text)

        def finish() -> None:
            grab(name, state)
            QTimer.singleShot(80, step)

        QTimer.singleShot(600, finish)

    print(f"[capture] writing to {out}", flush=True)
    QTimer.singleShot(900, step)
