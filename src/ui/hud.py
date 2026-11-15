"""
VICTOR HUD - animated desktop assistant backend
===============================================
The primary VICTOR experience: a frameless animated HUD that opens on the global
hotkey (Ctrl+Alt+V) or on the wake word "Victor", listens, thinks, speaks, and
returns to listening so a conversation can continue without re-activating.

Design rules implemented here
-----------------------------
* One process, one conversation at a time (no parallel Ollama calls).
* Every sound effect is disabled; only VICTOR's voice produces audio.
* No notification popups - the HUD itself is the feedback channel.
* Microphone is only held while listening; Whisper is unloaded when idle.
* The HUD hides itself after a quiet period so the desktop stays untouched.

Reused subsystems: src.voice.stt, src.voice.tts, src.voice.wake_word,
src.brain.llm, src.memory.store, src.core.state.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Keep numeric libraries single-threaded on a 16-thread laptop CPU.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import Property, QObject, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine

from src.brain.llm import victor_brain
from src.config.settings import settings
from src.core.hotkey import GlobalHotkeyManager
from src.core.state import SystemState, state_manager
from src.voice.stt import speech_recognizer
from src.voice.tts import tts_engine
from src.voice.wake_word import wake_word_service

SERVER_NAME = os.environ.get("VICTOR_IPC_NAME", "VICTOR_HUD_IPC")
HK_ACTIVATE, HK_INTERRUPT = 1, 2


def _make_logger() -> logging.Logger:
    """Small rotating log so activations and failures can be diagnosed later."""
    log = logging.getLogger("victor.hud")
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    try:
        logs_dir = PROJECT_ROOT / "logs"
        logs_dir.mkdir(exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            logs_dir / "hud.log", maxBytes=512_000, backupCount=2, encoding="utf-8"
        )
    except Exception:                                  # pragma: no cover
        handler = logging.NullHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.propagate = False
    return log


log = _make_logger()


class VictorHudBackend(QObject):
    # ---- signals consumed by Hud.qml -------------------------------------
    systemStateChanged = Signal(str)
    statusTextChanged = Signal(str)
    audioLevelChanged = Signal(float)
    hudVisibleChanged = Signal(bool)
    messageAdded = Signal(str, str, str)          # role, text, timestamp
    transcriptCleared = Signal()
    sessionActiveChanged = Signal(bool)
    _activate_requested = Signal(str)             # internal: thread -> GUI hop

    def __init__(self, qa_mode: bool = False) -> None:
        super().__init__()
        self.qa_mode = qa_mode

        self._state = SystemState.IDLE.value
        self._status = "VICTOR READY"
        self._audio_level = 0.0
        self._hud_visible = False
        self._listening = False
        self._session_active = False

        self._session_thread: Optional[threading.Thread] = None
        self._turn_lock = threading.Lock()        # serialises think/speak turns
        self._stop_requested = threading.Event()
        self._window = None
        self._last_activity = time.time()

        # Requests from non-GUI threads hop onto the GUI thread.
        self._activate_requested.connect(self._on_activate_requested, Qt.QueuedConnection)

        # Timers (GUI thread)
        self._auto_hide = QTimer(self)
        self._auto_hide.setSingleShot(True)
        self._auto_hide.timeout.connect(self.hide_hud)

        self._housekeeping = QTimer(self)
        self._housekeeping.setInterval(60_000)
        self._housekeeping.timeout.connect(self._release_idle_resources)
        self._housekeeping.start()

        # Wake word drives the same activation path as the hotkey.
        wake_word_service.on_detected = lambda: self._activate_requested.emit("wake")

        # In QA/capture mode nothing may take over the HUD, and no hardware is used.
        self._hotkeys = None
        if not qa_mode:
            self._hotkeys = GlobalHotkeyManager(
                {
                    HK_ACTIVATE: settings.get("tray.hotkey_talk", "ctrl+alt+v"),
                    HK_INTERRUPT: settings.get("tray.hotkey_stop", "ctrl+alt+x"),
                },
                on_hotkey=self._dispatch_hotkey,
            ).start()

        self._server = QLocalServer(self)
        QLocalServer.removeServer(SERVER_NAME)
        self._server.newConnection.connect(self._on_ipc_connection)
        self._server.listen(SERVER_NAME)

    # ---------------------------------------------------------------- startup
    def attach_window(self, window) -> None:
        """Called by main() once the QML root object exists."""
        self._window = window

    def start(self) -> None:
        settings.set("voice.audio_feedback", False)      # no chimes, ever
        if not self.qa_mode and settings.get("voice.wake_word_enabled", True):
            wake_word_service.start()
        self._set_state(SystemState.IDLE, "VICTOR READY")
        self.show_hud()
        # Unattended HUD should not animate forever: hide after the idle window.
        self._schedule_auto_hide()

    # ------------------------------------------------------------- properties
    def _get_state(self) -> str:
        return self._state

    def _get_status(self) -> str:
        return self._status

    def _get_level(self) -> float:
        return self._audio_level

    def _get_visible(self) -> bool:
        return self._hud_visible

    def _get_session(self) -> bool:
        return self._session_active

    systemState = Property(str, _get_state, notify=systemStateChanged)
    statusText = Property(str, _get_status, notify=statusTextChanged)
    audioLevel = Property(float, _get_level, notify=audioLevelChanged)
    hudVisible = Property(bool, _get_visible, notify=hudVisibleChanged)
    sessionActive = Property(bool, _get_session, notify=sessionActiveChanged)

    # ------------------------------------------------------------------ state
    def _set_state(self, state: SystemState, status: str) -> None:
        if state.value != self._state or status != self._status:
            log.info("state=%s status=%s", state.value, status)
        self._state = state.value
        self._status = status
        self.systemStateChanged.emit(self._state)
        self.statusTextChanged.emit(status)
        state_manager.set_state(state, status)

    # ----------------------------------------------------------- conversation
    def _dispatch_hotkey(self, slot_id: int) -> None:
        """Runs on the hotkey message-loop thread."""
        if slot_id == HK_ACTIVATE:
            self._activate_requested.emit("hotkey")
        elif slot_id == HK_INTERRUPT:
            self._activate_requested.emit("interrupt")

    @Slot(str)
    def _on_activate_requested(self, source: str) -> None:
        """GUI thread. One control: start, continue, or interrupt."""
        if self.qa_mode:
            return
        self._last_activity = time.time()
        log.info("activate source=%s session=%s", source, self._session_active)

        if source == "interrupt":
            self.interrupt()
            return

        self.show_hud()
        if tts_engine.is_speaking:
            self.interrupt()
            return
        if self._session_active:
            return
        self.start_session()

    @Slot()
    def start_session(self) -> None:
        if self._session_active:
            return
        self._session_active = True
        self._stop_requested.clear()
        self._auto_hide.stop()
        self.sessionActiveChanged.emit(True)
        log.info("session start")
        self._session_thread = threading.Thread(
            target=self._session_loop, daemon=True, name="VictorConversation"
        )
        self._session_thread.start()

    def _session_loop(self) -> None:
        """Listen -> think -> speak -> listen, until silence or cancellation."""
        language_mode = settings.get("language_mode", "auto")
        language = None if language_mode == "auto" else language_mode
        first_turn = True

        try:
            while self._session_active and not self._stop_requested.is_set():
                if not first_turn:
                    time.sleep(0.30)      # let the speaker tail decay before re-opening the mic
                first_turn = False

                wake_word_service.pause()
                self._listening = True
                self._set_state(SystemState.LISTENING, "LISTENING")

                text, detected = speech_recognizer.listen_and_transcribe(
                    energy_callback=self._emit_level,
                    language=language,
                    on_transcribe=lambda: self._set_state(SystemState.THINKING, "TRANSCRIBING"),
                )
                self._listening = False
                self._emit_level(0.0)

                if self._stop_requested.is_set():
                    break
                if not text:
                    log.info("listen ended without text (%s)", detected)
                    if detected == "timeout":
                        self._set_state(SystemState.IDLE, "NO SPEECH DETECTED")
                    break

                log.info("heard: %s", text)
                self._add_message("YOU", text)
                self._set_state(SystemState.THINKING, "PROCESSING")

                reply = victor_brain.query(text)
                if self._stop_requested.is_set():
                    break

                log.info("reply: %s", reply)
                self._add_message("VICTOR", reply)
                self._set_state(SystemState.SPEAKING, "SPEAKING")
                tts_engine.speak(reply, blocking=True, energy_callback=self._emit_level)
                self._emit_level(0.0)

                if self._stop_requested.is_set():
                    # Esc / Ctrl+Alt+X during speech: keep the conversation going.
                    self._stop_requested.clear()

        except Exception as exc:                     # pragma: no cover
            log.exception("session fault")
            self._set_state(SystemState.IDLE, f"FAULT: {exc}")
        finally:
            self._listening = False
            self._session_active = False
            self.sessionActiveChanged.emit(False)
            wake_word_service.resume()
            self._last_activity = time.time()
            log.info("session end")
            if self._state != SystemState.IDLE.value:
                self._set_state(SystemState.IDLE, "VICTOR READY")
            self._schedule_auto_hide()

    @Slot()
    def interrupt(self) -> None:
        """Stop speaking or cancel listening, keeping the session alive."""
        self._last_activity = time.time()

        if tts_engine.is_speaking:
            tts_engine.stop()
            log.info("interrupt: speech stopped")
            self._emit_level(0.0)
            self._stop_requested.clear()
            if self._session_active:
                self._set_state(SystemState.LISTENING, "INTERRUPTED - LISTENING")
            else:
                self._set_state(SystemState.IDLE, "VICTOR READY")
                self._schedule_auto_hide()
            return

        if self._listening:
            speech_recognizer.cancel()
            self._set_state(SystemState.IDLE, "LISTENING CANCELLED")
            return

        self._stop_requested.set()
        self._set_state(SystemState.IDLE, "VICTOR READY")
        self._schedule_auto_hide()

    @Slot(str)
    def sendText(self, text: str) -> None:
        """Typed fallback that behaves exactly like a spoken turn."""
        clean = (text or "").strip()
        if not clean:
            return
        self.show_hud()
        self._last_activity = time.time()

        def worker() -> None:
            with self._turn_lock:
                try:
                    self._add_message("YOU", clean)
                    self._set_state(SystemState.THINKING, "PROCESSING")
                    reply = victor_brain.query(clean)
                    self._add_message("VICTOR", reply)
                    self._set_state(SystemState.SPEAKING, "SPEAKING")
                    tts_engine.speak(reply, blocking=True, energy_callback=self._emit_level)
                except Exception as exc:
                    self._set_state(SystemState.IDLE, f"FAULT: {exc}")
                    return
                finally:
                    self._emit_level(0.0)
                self._set_state(SystemState.IDLE, "VICTOR READY")
                self._last_activity = time.time()
                self._schedule_auto_hide()

        threading.Thread(target=worker, daemon=True, name="VictorTypedTurn").start()

    # ------------------------------------------------------------------ audio
    def _emit_level(self, level: float) -> None:
        level = max(0.0, min(1.0, float(level)))
        if abs(level - self._audio_level) > 0.002:
            self._audio_level = level
            self.audioLevelChanged.emit(level)

    # ------------------------------------------------------------- transcript
    def _add_message(self, role: str, text: str) -> None:
        clean = (text or "").strip()
        if not clean:
            return
        self.messageAdded.emit(role, clean, datetime.now().strftime("%H:%M"))
        self._last_activity = time.time()

    @Slot()
    def clearTranscript(self) -> None:
        self.transcriptCleared.emit()

    # ------------------------------------------------------------ HUD chassis
    @Slot()
    def show_hud(self) -> None:
        self._auto_hide.stop()
        if not self._hud_visible:
            self._hud_visible = True
            self.hudVisibleChanged.emit(True)
            log.info("hud shown")
        if self._window is not None:
            try:
                self._window.show()
                self._window.requestActivate()
            except Exception:
                pass

    @Slot()
    def hide_hud(self) -> None:
        if self._session_active or tts_engine.is_speaking:
            return
        if self._hud_visible:
            self._hud_visible = False
            self.hudVisibleChanged.emit(False)
            log.info("hud hidden (idle)")
        if self._window is not None:
            try:
                self._window.hide()
            except Exception:
                pass

    def _schedule_auto_hide(self) -> None:
        seconds = int(settings.get("ui.hud_auto_hide_seconds", 30))
        if seconds > 0:
            self._auto_hide.start(seconds * 1000)

    @Slot()
    def quitApp(self) -> None:
        log.info("quit requested")
        try:
            self._session_active = False
            tts_engine.stop()
            speech_recognizer.cancel()
            wake_word_service.stop()
            if self._hotkeys is not None:
                self._hotkeys.stop()
            self._server.close()
        except Exception:
            log.exception("quit cleanup")
        QGuiApplication.quit()

    # ------------------------------------------------------- resource hygiene
    def _release_idle_resources(self) -> None:
        """Drop the Whisper model after a long quiet period (frees ~0.5 GB)."""
        idle_for = time.time() - self._last_activity
        limit = int(settings.get("voice.idle_unload_seconds", 300))
        if idle_for > limit and not self._session_active and speech_recognizer.is_model_loaded():
            speech_recognizer.unload_model()
            log.info("idle %.0fs: speech model released", idle_for)
            self._set_status_silent("IDLE - SPEECH MODEL RELEASED")

    def _set_status_silent(self, status: str) -> None:
        self._status = status
        self.statusTextChanged.emit(status)

    def _set_status(self, status: str) -> None:
        self._set_status_silent(status)

    # --------------------------------------------------------------- debug/QA
    @Slot(str)
    def debugSetState(self, state: str) -> None:
        """Used by scripts/hud_capture.py to render each animation state."""
        try:
            self._set_state(SystemState(state), state.upper())
        except ValueError:
            self._set_state(SystemState.IDLE, "VICTOR READY")

    @Slot(float)
    def debugSetLevel(self, level: float) -> None:
        self._emit_level(level)

    @Slot(str, str)
    def debugAddMessage(self, role: str, text: str) -> None:
        self._add_message(role, text)

    # -------------------------------------------------------------------- IPC
    def _on_ipc_connection(self) -> None:
        """A second launch asked the running HUD to come forward."""
        conn = self._server.nextPendingConnection()
        if conn is None:
            return
        conn.readyRead.connect(lambda: self._handle_ipc(conn))
        self._handle_ipc(conn)

    def _handle_ipc(self, conn: QLocalSocket) -> None:
        try:
            conn.readAll()
            conn.disconnectFromServer()
        except Exception:
            pass
        log.info("ipc show request")
        self._activate_requested.emit("ipc")


def _forward_to_running_instance() -> bool:
    """Return False when another HUD is already running (and tell it to show)."""
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(250):
        socket.write(b"show")
        socket.flush()
        socket.waitForBytesWritten(250)
        socket.disconnectFromServer()
        return False
    return True


def main(capture_path: str = "", capture_state: str = "") -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("VICTOR")
    app.setOrganizationName("VictorAI")
    app.setQuitOnLastWindowClosed(False)

    if not _forward_to_running_instance():
        print("[*] VICTOR is already running - asked the running HUD to come forward.")
        return 0

    backend = VictorHudBackend(qa_mode=bool(capture_path))
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("victor", backend)
    engine.load(str(Path(__file__).resolve().parent / "qml" / "Hud.qml"))

    if not engine.rootObjects():
        print("[-] HUD failed to load.")
        return 1

    window = engine.rootObjects()[0]
    backend.attach_window(window)
    backend.start()

    if capture_path:
        from src.ui.hud_capture import run_capture
        run_capture(app, window, backend, capture_path, capture_state)
        return app.exec()        # timers in the harness need a running event loop

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
