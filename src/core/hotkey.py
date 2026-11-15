"""
VICTOR Global Hotkey Manager (Win32)
Registers system-wide hotkeys via RegisterHotKey and dispatches them from a
dedicated message-loop thread, so the assistant works even when no window is
focused or visible.

Pure ctypes - no extra dependencies beyond the Windows API.
"""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable, Dict, Optional, Tuple

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
PM_REMOVE = 0x0001

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Common virtual-key codes
VK_CODES: Dict[str, int] = {
    **{chr(c): c for c in range(0x30, 0x3A)},          # 0-9
    **{chr(c): c for c in range(0x41, 0x5B)},          # A-Z
    "space": 0x20, "tab": 0x09, "enter": 0x0D, "esc": 0x1B,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}

MOD_TOKENS = {
    "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
    "alt": MOD_ALT, "shift": MOD_SHIFT, "win": MOD_WIN, "super": MOD_WIN,
}


def parse_shortcut(shortcut: str) -> Tuple[int, int]:
    """Parse 'ctrl+alt+v' into (modifiers, virtual_key). Raises ValueError on bad input."""
    parts = [p.strip().lower() for p in shortcut.replace(" ", "").split("+") if p.strip()]
    if len(parts) < 2:
        raise ValueError(f"Shortcut '{shortcut}' needs at least one modifier and one key.")

    mods = 0
    key_part = None
    for part in parts:
        if part in MOD_TOKENS:
            mods |= MOD_TOKENS[part]
        else:
            if key_part is not None:
                raise ValueError(f"Shortcut '{shortcut}' has more than one main key.")
            key_part = part

    if key_part is None or mods == 0:
        raise ValueError(f"Shortcut '{shortcut}' is missing a modifier or a key.")

    if key_part in VK_CODES:
        vk = VK_CODES[key_part]
    elif len(key_part) == 1:
        vk = ord(key_part.upper())
    else:
        raise ValueError(f"Unknown key '{key_part}' in shortcut '{shortcut}'.")

    return mods | MOD_NOREPEAT, vk


class GlobalHotkeyManager:
    """Registers global hotkeys and invokes callbacks from a dedicated thread.

    Callbacks run on the message-loop thread, not the GUI thread. Publish to Qt
    with a Signal (auto-queued) or any other thread-safe mechanism.
    """

    def __init__(self, bindings: Dict[int, str], on_hotkey: Callable[[int], None]):
        self._bindings = bindings           # {slot_id: "ctrl+alt+v"}
        self._on_hotkey = on_hotkey
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._ready = threading.Event()
        self.registered: Dict[int, str] = {}
        self.failures: Dict[int, str] = {}

    # ---------------------------------------------------------------- lifecycle
    def start(self, wait_seconds: float = 3.0) -> "GlobalHotkeyManager":
        if self._thread and self._thread.is_alive():
            return self
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="VictorHotkeyThread"
        )
        self._thread.start()
        self._ready.wait(timeout=wait_seconds)
        return self

    def stop(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None
        self._thread_id = None

    # ------------------------------------------------------------------- worker
    def _loop(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()

        for slot_id, shortcut in self._bindings.items():
            try:
                mods, vk = parse_shortcut(shortcut)
            except ValueError as exc:
                self.failures[slot_id] = str(exc)
                continue
            if user32.RegisterHotKey(None, slot_id, mods, vk):
                self.registered[slot_id] = shortcut
            else:
                err = ctypes.get_last_error()
                self.failures[slot_id] = (
                    f"'{shortcut}' rejected by Windows (error {err}) - already in use?"
                )

        self._ready.set()

        msg = wintypes.MSG()
        while True:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret in (0, -1):     # WM_QUIT or error
                break
            if msg.message == WM_HOTKEY:
                try:
                    self._on_hotkey(int(msg.wParam))
                except Exception as exc:                      # pragma: no cover
                    print(f"[!] Hotkey handler error: {exc}")
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        for slot_id in list(self.registered):
            try:
                user32.UnregisterHotKey(None, slot_id)
            except Exception:
                pass
        self.registered.clear()
