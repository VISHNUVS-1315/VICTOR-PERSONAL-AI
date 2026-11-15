"""
VICTOR UI entry point
=====================
The animated HUD is now the primary interface (`src/ui/hud.py` + `qml/Hud.qml`).
The previous multi-panel command center is preserved as `src/ui/main_legacy.py`
and can still be launched with `python run_victor.py --classic`.

This module keeps the old import path working for anything that referenced
`src.ui.main.main()`.
"""

from __future__ import annotations

import sys


def main() -> int:
    from src.ui.hud import main as hud_main
    return hud_main()


if __name__ == "__main__":
    raise SystemExit(main())
