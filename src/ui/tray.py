"""
VICTOR Tray Mode - lightweight always-resident assistant
======================================================
Runs with no main window: a system-tray icon, global hotkeys and the offline
"Victor" wake word. Answers are spoken through the existing TTS engine.

Controls
--------
Ctrl+Alt+V   Talk now (same as saying "Victor")
Ctrl+Alt+T   Type a command instead of speaking
Ctrl+Alt+X   Stop speaking / cancel the current turn

Everything is re-used from the existing stack:
  wake word  -> src/voice/wake_word.py  (openWakeWord + victor.onnx)
  speech     -> src/voice/stt.py        (Faster-Whisper, lazy loaded)
  brain      -> src/brain/llm.py        (Ollama qwen3.5:9b + SQLite memory)
  voice out  -> src/voice/tts.py        (SAPI5 David/Zira)
"""

from __future__ import annotations

import ctypes
import logging
import subprocess
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMenu, QSystemTrayIcon

from src.config.settings import LOGS_DIR, ROOT_DIR, settings
from src.core.audio_effects import play_sound
from src.core.hotkey import GlobalHotkeyManager
from src.core.state import SystemState, state_manager

log = logging.getLogger("victor.tray")

APP_NAME = "VICTOR"
MUTEX_NAME = "VICTOR_Tray_SingleInstance"

# Menu hotkey slot ids
HK_TALK, HK_TYPE, HK_STOP = 1, 2, 3

STATE_COLORS = {
    SystemState.IDLE:      "#55dfff",
    SystemState.LISTENING: "#8cffb5",
    SystemState.THINKING:  "#ffc857",
    SystemState.SPEAKING:  "#7aa2ff",
    SystemState.SLEEPING:  "#71869b",
    SystemState.OFFLINE:   "#ff5c5c",
}


# --------------------------------------------------------------------------- utils
def configure_logging(verbose: bool = False) -> None:
    """File logging survives pythonw.exe, where there is no console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    class _LineBufferedRotatingFileHandler(RotatingFileHandler):
        """Flush every record so `Open log` in the tray menu is never stale."""

        def _open(self):
            return open(
                self.baseFilename, self.mode, encoding=self.encoding,
                errors=self.errors, buffering=1,
            )

    handler = _LineBufferedRotatingFileHandler(
        LOGS_DIR / "tray.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    root = logging.getLogger("victor")
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    if not root.handlers:
        root.addHandler(handler)
    if verbose:
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        root.addHandler(stream)


def single_instance_lock() -> bool:
    """True if this is the first VICTOR tray process; False if one already runs."""
    handle = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
    already_running = ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    if already_running:
        return False
    # Keep the handle referenced for the process lifetime.
    globals()["_victor_mutex_handle"] = handle
    return True


def make_icon(state: SystemState, busy_ring: bool = False) -> QIcon:
    """Draw the arc-reactor style status icon at runtime (no image assets needed)."""
    color = QColor(STATE_COLORS.get(state, "#55dfff"))
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # Dark base disk
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#0a1220")))
    painter.drawEllipse(3, 3, 58, 58)

    # Outer ring
    ring_pen = QPen(color)
    ring_pen.setWidth(3)
    painter.setPen(ring_pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(7, 7, 50, 50)

    # Inner ring (dashed when working)
    inner_pen = QPen(QColor(color.red(), color.green(), color.blue(), 150))
    inner_pen.setWidth(2)
    if busy_ring:
        inner_pen.setStyle(Qt.DashLine)
    painter.setPen(inner_pen)
    painter.drawEllipse(15, 15, 34, 34)

    # Glowing core
    core = QColor(color)
    core.setAlpha(235)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(core))
    painter.drawEllipse(24, 24, 16, 16)

    painter.end()
    return QIcon(pix)


# --------------------------------------------------------------------------- bridge
class _Bridge(QObject):
    """Cross-thread -> GUI-thread signals (wake word and hotkey threads emit these)."""
    request_turn = Signal(str)              # "wake" | "hotkey" | "manual"
    type_requested = Signal()
    state_update = Signal(object, str)      # SystemState, message
    notification = Signal(str, str, int, bool)   # title, body, timeout_ms, warning


# --------------------------------------------------------------------------- daemon
class VictorTray(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self._busy = False
        self._busy_lock = threading.Lock()
        self._last_text = ""
        self._last_reply = ""
        self._selftest = False

        self.bridge = _Bridge()
        self.bridge.request_turn.connect(self._on_turn_requested, Qt.QueuedConnection)
        self.bridge.type_requested.connect(self._prompt_typed_command, Qt.QueuedConnection)
        self.bridge.state_update.connect(self._apply_state, Qt.QueuedConnection)
        self.bridge.notification.connect(self._show_notification, Qt.QueuedConnection)

        self.tray = QSystemTrayIcon(make_icon(SystemState.IDLE), app)
        self.tray.setToolTip("VICTOR - starting up")
        self.tray.activated.connect(self._on_tray_activated)

        self._build_menu()

        # Deferred imports keep startup snappy and let the tray appear first
        from src.brain.llm import victor_brain
        from src.voice.stt import speech_recognizer
        from src.voice.tts import tts_engine
        from src.voice.wake_word import wake_word_service

        self.brain = victor_brain
        self.stt = speech_recognizer
        self.tts = tts_engine
        self.wake = wake_word_service
        self.wake.on_detected = self._on_wake_word

        state_manager.add_listener(self._on_state_change)

        self.hotkeys = GlobalHotkeyManager(
            {
                HK_TALK: settings.get("tray.hotkey_talk", "ctrl+alt+v"),
                HK_TYPE: settings.get("tray.hotkey_type", "ctrl+alt+t"),
                HK_STOP: settings.get("tray.hotkey_stop", "ctrl+alt+x"),
            },
            on_hotkey=self._dispatch_hotkey,
        ).start()

    # ------------------------------------------------------------------ menu
    def _build_menu(self) -> None:
        menu = QMenu()

        self.act_talk = QAction("Talk now\tCtrl+Alt+V", menu)
        self.act_talk.triggered.connect(lambda: self.bridge.request_turn.emit("manual"))
        menu.addAction(self.act_talk)

        self.act_type = QAction("Type a command...\tCtrl+Alt+T", menu)
        self.act_type.triggered.connect(self._prompt_typed_command)
        menu.addAction(self.act_type)

        self.act_stop = QAction("Stop speaking\tCtrl+Alt+X", menu)
        self.act_stop.triggered.connect(self.stop_everything)
        menu.addAction(self.act_stop)

        menu.addSeparator()

        self.act_wake = QAction("Wake word 'Victor'", menu)
        self.act_wake.setCheckable(True)
        self.act_wake.setChecked(bool(settings.get("voice.wake_word_enabled", True)))
        self.act_wake.toggled.connect(self._toggle_wake_word)
        menu.addAction(self.act_wake)

        self.act_voice = QAction("Spoken replies", menu)
        self.act_voice.setCheckable(True)
        self.act_voice.setChecked(bool(settings.get("tray.voice_replies", True)))
        self.act_voice.toggled.connect(self._toggle_voice_replies)
        menu.addAction(self.act_voice)

        # Power mode
        power_menu = menu.addMenu("Power mode")
        self._power_group = QActionGroup(power_menu)
        self._power_group.setExclusive(True)
        for mode, label in (
            ("low_power", "Low power"),
            ("balanced", "Balanced"),
            ("performance", "Performance"),
        ):
            act = QAction(label, power_menu, checkable=True)
            act.setChecked(settings.get_power_mode() == mode)
            act.triggered.connect(lambda _=False, m=mode: self._set_power_mode(m))
            power_menu.addAction(act)
            self._power_group.addAction(act)

        menu.addSeparator()

        self.act_status = QAction("Status: starting", menu)
        self.act_status.setEnabled(False)
        menu.addAction(self.act_status)

        self.act_repeat = QAction("Repeat last answer", menu)
        self.act_repeat.triggered.connect(self._repeat_last)
        self.act_repeat.setEnabled(False)
        menu.addAction(self.act_repeat)

        act_hud = QAction("Open full HUD", menu)
        act_hud.triggered.connect(self._open_hud)
        menu.addAction(act_hud)

        act_log = QAction("Open log", menu)
        act_log.triggered.connect(self._open_log)
        menu.addAction(act_log)

        self.act_autostart = QAction("Start with Windows", menu, checkable=True)
        self.act_autostart.setChecked(self._autostart_installed())
        self.act_autostart.toggled.connect(self._toggle_autostart)
        menu.addAction(self.act_autostart)

        menu.addSeparator()

        act_quit = QAction("Quit VICTOR", menu)
        act_quit.triggered.connect(self.shutdown)
        menu.addAction(act_quit)

        self.menu = menu
        self.tray.setContextMenu(menu)

    # ------------------------------------------------------------------ start
    def start(self) -> None:
        self.tray.show()
        self._set_state(SystemState.IDLE, "Online - press Ctrl+Alt+V or say 'Victor'")

        ok, message = self.brain.check_connection()
        log.info("Ollama: %s", message)
        if not ok:
            self.notify("Brain offline", message, warning=True)

        for slot_id, reason in self.hotkeys.failures.items():
            log.warning("Hotkey %s unavailable: %s", slot_id, reason)

        if self.act_wake.isChecked():
            self._start_wake_word()

        self.notify(
            "VICTOR is ready",
            "Ctrl+Alt+V to talk, Ctrl+Alt+T to type, Ctrl+Alt+X to stop.",
        )

    def _start_wake_word(self) -> None:
        try:
            self.wake.start()
            log.info("Wake word listener started.")
        except Exception as exc:
            log.error("Wake word failed: %s", exc)
            self.notify("Wake word unavailable", str(exc), warning=True)
            self.act_wake.setChecked(False)

    # ------------------------------------------------------------- tray events
    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:      # left click
            self.bridge.request_turn.emit("manual")
        elif reason == QSystemTrayIcon.DoubleClick:
            self._prompt_typed_command()

    def _on_wake_word(self) -> None:
        """Called on the wake-word audio thread."""
        log.info("Wake word detected.")
        self.bridge.request_turn.emit("wake")

    def _dispatch_hotkey(self, slot_id: int) -> None:
        """Called on the hotkey message-loop thread."""
        if slot_id == HK_TALK:
            self.bridge.request_turn.emit("hotkey")
        elif slot_id == HK_TYPE:
            self.bridge.type_requested.emit()
        elif slot_id == HK_STOP:
            self.stop_everything()

    # ------------------------------------------------------------------- turns
    def _on_turn_requested(self, source: str) -> None:
        """GUI thread entry point for a new interaction."""
        if self._busy:
            if self.tts.is_speaking:
                self.stop_everything()
            else:
                # The wake word pauses itself when it fires; never leave it deaf.
                self.wake.resume()
                self.notify("Still working", "Give me a moment to finish this turn.")
            return

        with self._busy_lock:
            self._busy = True

        threading.Thread(
            target=self._voice_turn, args=(source,), daemon=True, name="VictorTurnThread"
        ).start()

    def _voice_turn(self, source: str) -> None:
        try:
            if source != "wake":
                self.wake.pause()
                play_sound("activation")

            self._set_state(SystemState.LISTENING, "Listening...")
            language = None if settings.get("language_mode", "auto") == "auto" else settings.get("language_mode")

            text, reason = self.stt.listen_and_transcribe(language=language)
            if not text:
                log.info("No speech captured (%s).", reason)
                if reason != "cancelled":
                    self.notify("I didn't catch that", "Try again with Ctrl+Alt+V.")
                return

            self._last_text = text
            self._set_state(SystemState.THINKING, f"You: {text}")

            reply = self.brain.query(text)
            self._last_reply = reply
            log.info("Q: %s | A: %s", text, reply[:400])

            self._set_state(SystemState.SPEAKING, "Speaking...")
            self.notify("VICTOR", f"You: {text}\nVICTOR: {reply}", timeout_ms=8000)

            if settings.get("tray.voice_replies", True):
                self.tts.speak(reply, blocking=True)

        except Exception as exc:
            log.exception("Turn failed")
            self.notify("Error", str(exc), warning=True)
        finally:
            if not self.tts.is_speaking:
                self.wake.resume()
            self._set_state(SystemState.IDLE, "Online - press Ctrl+Alt+V or say 'Victor'")
            with self._busy_lock:
                self._busy = False

    def _prompt_typed_command(self) -> None:
        if self._busy:
            self.notify("Still working", "Give me a moment to finish this turn.")
            return

        text, ok = QInputDialog.getText(
            None, "VICTOR", "Command:", QLineEdit.Normal, ""
        )
        if not ok or not text.strip():
            return

        with self._busy_lock:
            self._busy = True

        def _run() -> None:
            try:
                self._last_text = text.strip()
                self._set_state(SystemState.THINKING, f"You: {text.strip()}")
                reply = self.brain.query(text.strip())
                self._last_reply = reply
                log.info("Typed: %s | A: %s", text.strip(), reply[:400])
                self._set_state(SystemState.SPEAKING, "Speaking...")
                self.notify("VICTOR", reply, timeout_ms=10000)
                if settings.get("tray.voice_replies", True):
                    self.tts.speak(reply, blocking=True)
            except Exception as exc:
                log.exception("Typed turn failed")
                self.notify("Error", str(exc), warning=True)
            finally:
                self._set_state(SystemState.IDLE, "Online - press Ctrl+Alt+V or say 'Victor'")
                with self._busy_lock:
                    self._busy = False

        threading.Thread(target=_run, daemon=True, name="VictorTypedThread").start()

    def stop_everything(self) -> None:
        try:
            self.tts.stop()
            self.stt.cancel()
        except Exception:
            pass
        self.wake.resume()
        self._set_state(SystemState.IDLE, "Stopped - standing by")

    def _repeat_last(self) -> None:
        if self._last_reply:
            self.tts.speak(self._last_reply, blocking=False)

    # ------------------------------------------------------------------ toggles
    def _toggle_wake_word(self, enabled: bool) -> None:
        settings.set("voice.wake_word_enabled", bool(enabled))
        if enabled:
            self._start_wake_word()
            self.notify("Wake word on", "Say 'Victor' to start talking.")
        else:
            self.wake.stop()
            self.notify("Wake word off", "Use Ctrl+Alt+V to talk.")

    def _toggle_voice_replies(self, enabled: bool) -> None:
        settings.set("tray.voice_replies", bool(enabled))

    def _set_power_mode(self, mode: str) -> None:
        settings.set_power_mode(mode)
        self.notify("Power mode", mode.replace("_", " ").title())

    def _autostart_installed(self) -> bool:
        try:
            from scripts.install_autostart import is_installed
            return is_installed()
        except Exception:
            return False

    def _toggle_autostart(self, enabled: bool) -> None:
        try:
            from scripts.install_autostart import install, uninstall
            path = install() if enabled else uninstall()
            self.notify(
                "Autostart enabled" if enabled else "Autostart disabled",
                f"Startup entry: {path}",
            )
        except Exception as exc:
            log.error("Autostart change failed: %s", exc)
            self.notify("Autostart failed", str(exc), warning=True)
            self.act_autostart.blockSignals(True)
            self.act_autostart.setChecked(not enabled)
            self.act_autostart.blockSignals(False)

    # ------------------------------------------------------------------- state
    def _on_state_change(self, state: SystemState, message: str) -> None:
        self.bridge.state_update.emit(state, message)

    def _set_state(self, state: SystemState, message: str) -> None:
        """Thread-safe state update (queued to the GUI thread)."""
        self.bridge.state_update.emit(state, message)

    def _apply_state(self, state: SystemState, message: str) -> None:
        busy = state in (SystemState.LISTENING, SystemState.THINKING, SystemState.SPEAKING)
        self.tray.setIcon(make_icon(state, busy_ring=busy))
        self.tray.setToolTip(f"VICTOR - {message}")
        self.act_status.setText(f"Status: {message[:60]}")
        self.act_repeat.setEnabled(bool(self._last_reply))
        self.act_talk.setEnabled(not busy)
        self.act_type.setEnabled(not busy)

    def notify(self, title: str, body: str, timeout_ms: int = 5000, warning: bool = False) -> None:
        self.bridge.notification.emit(title, body, timeout_ms, warning)

    def _show_notification(self, title: str, body: str, timeout_ms: int, warning: bool) -> None:
        """GUI thread: show a balloon/toast."""
        if len(body) > 400:
            body = body[:397] + "..."
        icon = QSystemTrayIcon.Warning if warning else QSystemTrayIcon.Information
        self.tray.showMessage(title, body, icon, timeout_ms)

    # ------------------------------------------------------------------ extras
    def _open_hud(self) -> None:
        python = sys.executable
        try:
            subprocess.Popen(
                [python, str(ROOT_DIR / "run_victor.py")],
                cwd=str(ROOT_DIR),
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        except Exception as exc:
            self.notify("Could not open HUD", str(exc), warning=True)

    def _open_log(self) -> None:
        try:
            subprocess.Popen(["notepad.exe", str(LOGS_DIR / "tray.log")])
        except Exception as exc:
            self.notify("Could not open log", str(exc), warning=True)

    def shutdown(self) -> None:
        log.info("Shutting down tray mode.")
        try:
            self.hotkeys.stop()
        except Exception:
            pass
        try:
            self.wake.stop()
        except Exception:
            pass
        try:
            self.tts.stop()
        except Exception:
            pass
        self.tray.hide()
        self.app.quit()


# --------------------------------------------------------------------------- entry
def run_tray(selftest: bool = False, verbose: bool = False) -> int:
    configure_logging(verbose=verbose)

    if not single_instance_lock():
        print("[!] VICTOR tray is already running.")
        log.info("Second instance refused (already running).")
        return 0

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("[-] No system tray available on this session.")
        return 1

    daemon = VictorTray(app)
    daemon.start()

    if selftest:
        def _report() -> None:
            print("[selftest] tray visible:", daemon.tray.isVisible())
            print("[selftest] hotkeys registered:", daemon.hotkeys.registered)
            print("[selftest] hotkey failures:", daemon.hotkeys.failures)
            ok, msg = daemon.brain.check_connection()
            print("[selftest] brain:", ok, msg)
            print("[selftest] autostart:", daemon._autostart_installed())
            QTimer.singleShot(300, daemon.shutdown)

        QTimer.singleShot(2500, _report)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_tray(selftest="--selftest" in sys.argv))
