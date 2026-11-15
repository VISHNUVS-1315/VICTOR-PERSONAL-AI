"""
VICTOR Main Desktop Application & Native QML Engine
Integrates PySide6 QML with all backend subsystems:
Wake Word, Faster-Whisper STT, Natural TTS, Ollama Qwen 3.5 Brain,
Persistent SQLite Memory, and Computer Automation with Power Profile Throttling.
"""

import os
import sys

# Prevent background libraries from spawning excessive thread pools on high-core CPUs
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer, Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from src.actions.computer_control import computer
from src.brain.llm import victor_brain
from src.config.settings import settings
from src.core.audio_effects import play_sound
from src.core.state import state_manager, SystemState
from src.memory.store import get_memories, save_memory, delete_memory
from src.services.telemetry_service import telemetry_service
from src.voice.stt import speech_recognizer
from src.voice.tts import tts_engine
from src.voice.wake_word import wake_word_service


class VictorBackend(QObject):
    # Signals for QML HUD
    messageAdded = Signal(str, str, str)  # role, content, timestamp
    logAdded = Signal(str, str, str, str)  # timestamp, source, message, level
    memoriesLoaded = Signal(list)  # list of memory dicts
    systemStateChanged = Signal(str)
    statusMessageChanged = Signal(str)
    audioLevelChanged = Signal(float)
    telemetryUpdated = Signal(dict)
    wakeWordToggled = Signal(bool)
    powerModeChanged = Signal(str)
    voiceLanguageChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self._system_state = SystemState.IDLE.value
        self._status_message = "VICTOR NEURAL CORE ONLINE"
        self._audio_level = 0.0
        self._tts_enabled = True

        # Telemetry metrics
        self._cpu_usage = 0.0
        self._ram_usage = 0.0
        self._ram_used_gb = 0.0
        self._ram_total_gb = 24.0
        self._gpu_usage = 0
        self._gpu_temp = 0
        self._gpu_vram_used = 0
        self._gpu_vram_total = 8151
        self._ollama_online = True
        self._wake_word_active = True
        self._is_sleeping = False
        self._power_mode = settings.get_power_mode()
        self._voice_language = settings.get("language_mode", "auto")

        # Concurrency & interaction locks
        self._interaction_lock = threading.Lock()
        self._interaction_in_progress = False

        # Register state listener
        state_manager.add_listener(self._on_state_transition)

        # Wire Wake-Word callback
        wake_word_service.on_detected = self._on_wake_word_detected

        # Wire Telemetry service callback
        telemetry_service.add_callback(self._on_telemetry_snapshot)

        # Start background services
        QTimer.singleShot(400, self.boot_services)

    def boot_services(self):
        """Start background listener and telemetry monitoring."""
        self.log("CORE", f"Starting VICTOR Subsystems [Power Mode: {self._power_mode.upper()}]...", "OK")
        self.refresh_memories()

        # Start Telemetry
        telemetry_service.start()
        self.log("DIAG", "Hardware telemetry monitor active.", "OK")

        # Start Wake-Word listener if enabled
        if settings.get("voice.wake_word_enabled", True):
            wake_word_service.start()
            self._wake_word_active = True
            self.wakeWordToggled.emit(True)
            self.log("HOTWORD", "Lightweight listener active for keyword 'Victor'.", "OK")
        else:
            self._wake_word_active = False
            self.wakeWordToggled.emit(False)

        # Initial Ollama check
        self.check_engine()

    def _on_state_transition(self, new_state: SystemState, status_msg: str):
        self._system_state = new_state.value
        self._status_message = status_msg
        self.systemStateChanged.emit(new_state.value)
        self.statusMessageChanged.emit(status_msg)

    def _on_wake_word_detected(self):
        """Triggered from background audio thread when user says 'Victor'."""
        with self._interaction_lock:
            if self._interaction_in_progress:
                return
            self._interaction_in_progress = True

        self.log("HOTWORD", "Wake word 'Victor' detected. Engaging speech listener...", "OK")
        play_sound("wake")
        threading.Thread(target=self._run_voice_interaction, daemon=True, name="VictorVoiceLoop").start()

    def _run_voice_interaction(self):
        """
        Single-command interaction pipeline:
        Standby -> Detect 'Victor' -> Listening (VAD) -> Finalize speech -> Send to Ollama -> Speak -> Standby
        """
        try:
            if self._is_sleeping:
                self._is_sleeping = False

            state_manager.set_state(SystemState.LISTENING, "LISTENING FOR VOICE...")
            self.log("AUDIO", "Microphone stream opened. Listening for speech...", "INFO")

            def on_energy(rms_level: float):
                self.set_audio_level(rms_level)

            lang_arg = None if self._voice_language == "auto" else self._voice_language
            transcript, lang = speech_recognizer.listen_and_transcribe(
                energy_callback=on_energy,
                language=lang_arg
            )
            self.set_audio_level(0.0)

            if transcript and transcript not in ("cancelled", "incomplete", "empty", "error"):
                time_str = datetime.now().strftime("%H:%M")
                self.log("STT", f"Captured voice [{lang.upper()}]: '{transcript}'", "OK")
                self.messageAdded.emit("YOU", transcript, time_str)
                self._process_command(transcript, time_str)
            else:
                state_manager.set_state(SystemState.IDLE, "VICTOR IS STANDING BY")
                self.log("STT", "Speech listener finalized (no command detected).", "INFO")

        except Exception as e:
            self.log("VOICE", f"Voice pipeline error: {e}", "WARN")
            state_manager.set_state(SystemState.IDLE, "VICTOR IS STANDING BY")
        finally:
            self.set_audio_level(0.0)
            with self._interaction_lock:
                self._interaction_in_progress = False
            # Resume wake-word detector now that conversation turn is finished
            if self._wake_word_active and not self._is_sleeping:
                wake_word_service.resume()

    def _process_command(self, query: str, time_str: str):
        """Send command to Ollama, execute actions if any, and speak single response."""
        state_manager.set_state(SystemState.THINKING, "PROCESSING WITH QWEN 3.5 (9B)...")
        reply = victor_brain.query(query)
        self.log("LLM", "Inference response generated.", "OK")

        # Deliver to UI chat
        self.messageAdded.emit("VICTOR", reply, time_str)

        # Synthesize voice response if TTS enabled
        if self._tts_enabled and not self._is_sleeping:
            state_manager.set_state(SystemState.SPEAKING, "SYNTHESIZING SPEECH...")
            try:
                tts_engine.speak(
                    reply,
                    energy_callback=self.set_audio_level,
                    blocking=True
                )
            except Exception as tts_err:
                self.log("TTS", f"Error in voice playback: {tts_err}", "WARN")

        # Return to standby
        self.set_audio_level(0.0)
        state_manager.set_state(SystemState.IDLE, "VICTOR IS STANDING BY")

    def _on_telemetry_snapshot(self, snap: Dict[str, Any]):
        """Triggered periodically from telemetry service thread."""
        self._cpu_usage = snap.get("cpu_percent", 0.0)
        self._ram_usage = snap.get("ram_percent", 0.0)
        self._ram_used_gb = snap.get("ram_used_gb", 0.0)
        self._ram_total_gb = snap.get("ram_total_gb", 24.0)

        gpu = snap.get("gpu", {})
        self._gpu_usage = gpu.get("utilization", 0)
        self._gpu_temp = gpu.get("temperature", 0)
        self._gpu_vram_used = gpu.get("vram_used_mb", 0)
        self._gpu_vram_total = gpu.get("vram_total_mb", 8151)
        self._ollama_online = snap.get("ollama_online", False)

        # Emit to QML
        self.telemetryUpdated.emit(snap)

    def log(self, source: str, message: str, level: str = "INFO"):
        time_str = datetime.now().strftime("%H:%M:%S")
        self.logAdded.emit(time_str, source, message, level)

    # Properties
    def get_system_state(self) -> str:
        return self._system_state

    def set_system_state(self, state: str):
        if self._system_state != state:
            self._system_state = state
            self.systemStateChanged.emit(state)

    systemState = Property(str, get_system_state, set_system_state, notify=systemStateChanged)

    def get_status_message(self) -> str:
        return self._status_message

    def set_status_message(self, msg: str):
        if self._status_message != msg:
            self._status_message = msg
            self.statusMessageChanged.emit(msg)

    statusMessage = Property(str, get_status_message, set_status_message, notify=statusMessageChanged)

    def get_audio_level(self) -> float:
        return self._audio_level

    def set_audio_level(self, level: float):
        if self._audio_level != level:
            self._audio_level = level
            self.audioLevelChanged.emit(level)

    audioLevel = Property(float, get_audio_level, notify=audioLevelChanged)

    # Telemetry properties
    def get_cpu_usage(self) -> float:
        return self._cpu_usage

    cpuUsage = Property(float, get_cpu_usage)

    def get_ram_usage(self) -> float:
        return self._ram_usage

    ramUsage = Property(float, get_ram_usage)

    def get_ram_used_gb(self) -> float:
        return self._ram_used_gb

    ramUsedGb = Property(float, get_ram_used_gb)

    def get_ram_total_gb(self) -> float:
        return self._ram_total_gb

    ramTotalGb = Property(float, get_ram_total_gb)

    def get_gpu_usage(self) -> int:
        return self._gpu_usage

    gpuUsage = Property(int, get_gpu_usage)

    def get_gpu_temp(self) -> int:
        return self._gpu_temp

    gpuTemp = Property(int, get_gpu_temp)

    def get_gpu_vram_used(self) -> int:
        return self._gpu_vram_used

    gpuVramUsed = Property(int, get_gpu_vram_used)

    def get_ollama_online(self) -> bool:
        return self._ollama_online

    ollamaOnline = Property(bool, get_ollama_online)

    def get_wake_word_active(self) -> bool:
        return self._wake_word_active

    wakeWordActive = Property(bool, get_wake_word_active, notify=wakeWordToggled)

    def get_is_sleeping(self) -> bool:
        return self._is_sleeping

    isSleeping = Property(bool, get_is_sleeping)

    def get_power_mode(self) -> str:
        return self._power_mode

    powerMode = Property(str, get_power_mode, notify=powerModeChanged)

    def get_voice_language(self) -> str:
        return self._voice_language

    voiceLanguage = Property(str, get_voice_language, notify=voiceLanguageChanged)

    def get_mic_status(self) -> str:
        if self._system_state == SystemState.LISTENING.value:
            return "RECORDING (VAD)"
        elif self._wake_word_active and not self._is_sleeping:
            return "STANDBY (WAKE WORD)"
        else:
            return "IDLE / PAUSED"

    micStatus = Property(str, get_mic_status, notify=systemStateChanged)

    # Slots callable from QML
    @Slot(str)
    def sendMessage(self, user_text: str):
        """Process user text input asynchronously."""
        clean_text = user_text.strip()
        if not clean_text:
            return

        with self._interaction_lock:
            if self._interaction_in_progress:
                self.log("CORE", "System busy processing previous request.", "WARN")
                return
            self._interaction_in_progress = True

        # Pause wake word to avoid any audio feedback
        wake_word_service.pause()

        def text_worker():
            try:
                time_str = datetime.now().strftime("%H:%M")
                self.log("USER", f"Query: {clean_text[:65]}...", "INFO")
                self._process_command(clean_text, time_str)
            finally:
                with self._interaction_lock:
                    self._interaction_in_progress = False
                if self._wake_word_active and not self._is_sleeping:
                    wake_word_service.resume()

        threading.Thread(target=text_worker, daemon=True, name="VictorTextWorker").start()

    @Slot()
    def startVoiceInput(self):
        """Trigger microphone listening via Faster-Whisper manually."""
        if self._system_state == SystemState.LISTENING.value:
            # If already listening, cancel
            speech_recognizer.cancel()
            state_manager.set_state(SystemState.IDLE, "VOICE CAPTURE CANCELLED")
            with self._interaction_lock:
                self._interaction_in_progress = False
            if self._wake_word_active:
                wake_word_service.resume()
            return

        with self._interaction_lock:
            if self._interaction_in_progress:
                self.log("AUDIO", "System busy processing previous request.", "WARN")
                return
            self._interaction_in_progress = True

        wake_word_service.pause()
        threading.Thread(target=self._run_voice_interaction, daemon=True, name="VictorVoiceLoop").start()

    @Slot()
    def stopSpeaking(self):
        """Immediately interrupt ongoing speech."""
        tts_engine.stop()
        self.set_audio_level(0.0)
        state_manager.set_state(SystemState.IDLE, "SPEECH INTERRUPTED")
        self.log("TTS", "Speech output stopped by operator.", "INFO")
        with self._interaction_lock:
            self._interaction_in_progress = False
        if self._wake_word_active and not self._is_sleeping:
            wake_word_service.resume()

    @Slot(str)
    def setPowerMode(self, mode: str):
        """Switch power mode: 'low_power', 'balanced', or 'performance'."""
        mode = mode.lower().strip()
        if mode in ("low_power", "balanced", "performance"):
            self._power_mode = mode
            settings.set_power_mode(mode)
            self.powerModeChanged.emit(mode)
            self.log("POWER", f"Active power profile: [{mode.upper()}]. UI & monitoring adjusted.", "OK")

    @Slot(str)
    def setVoiceLanguage(self, lang: str):
        """Switch language mode: 'auto', 'en', 'ta'."""
        lang = lang.lower().strip()
        if lang in ("auto", "en", "ta"):
            self._voice_language = lang
            settings.set("language_mode", lang)
            self.voiceLanguageChanged.emit(lang)
            self.log("VOICE", f"Speech recognition language mode set to [{lang.upper()}].", "OK")

    @Slot()
    def toggleSleep(self):
        """Toggle system standby sleep mode."""
        self._is_sleeping = not self._is_sleeping
        if self._is_sleeping:
            tts_engine.stop()
            speech_recognizer.cancel()
            wake_word_service.pause()
            state_manager.set_state(SystemState.SLEEPING, "VICTOR SLEEPING (STANDBY)")
            play_sound("sleep")
            self.log("CORE", "Victor entered low-power standby mode.", "INFO")
        else:
            state_manager.set_state(SystemState.IDLE, "VICTOR AWAKE")
            if self._wake_word_active:
                wake_word_service.resume()
            play_sound("acknowledge")
            self.log("CORE", "Victor restored from standby mode.", "OK")

    @Slot()
    def toggleWakeWord(self):
        """Toggle background wake-word listener."""
        if wake_word_service.is_running() and not wake_word_service.is_paused():
            wake_word_service.pause()
            self._wake_word_active = False
            self.wakeWordToggled.emit(False)
            self.log("HOTWORD", "Wake-word listener paused by operator.", "WARN")
        else:
            if not wake_word_service.is_running():
                wake_word_service.start()
            else:
                wake_word_service.resume()
            self._wake_word_active = True
            self.wakeWordToggled.emit(True)
            self.log("HOTWORD", "Wake-word listener active for 'Victor'.", "OK")

    @Slot()
    def refresh_memories(self):
        """Fetch all stored memories from SQLite and emit to QML."""
        try:
            memories = get_memories()
            self.memoriesLoaded.emit(memories)
            self.log("MEM", f"Loaded {len(memories)} memories from database.", "OK")
        except Exception as e:
            self.log("MEM", f"Error reading memories: {e}", "WARN")

    @Slot(str, str)
    def addMemory(self, content: str, category: str = "general"):
        """Save a new memory to SQLite."""
        if not content.strip():
            return
        res = save_memory(content, category=category or "general")
        self.log("MEM", f"Saved: {content[:40]}... ({res})", "OK")
        self.refresh_memories()

    @Slot(int)
    def deleteMemory(self, memory_id: int):
        """Delete memory from SQLite by ID."""
        res = delete_memory(memory_id)
        self.log("MEM", f"Deleted memory #{memory_id} (Success: {res})", "INFO")
        self.refresh_memories()

    @Slot()
    def check_engine(self):
        """Test Ollama connection status."""
        def check_worker():
            ok, msg = victor_brain.check_connection()
            level = "OK" if ok else "WARN"
            self.log("OLLAMA", msg, level)

        threading.Thread(target=check_worker, daemon=True).start()

    @Slot(str)
    def speak(self, text: str):
        """Manually trigger TTS speech."""
        if not text:
            return

        def speak_worker():
            state_manager.set_state(SystemState.SPEAKING, "SPEAKING...")
            self.log("TTS", f"Voice test: {text[:40]}...", "INFO")
            tts_engine.speak(text, energy_callback=self.set_audio_level, blocking=True)
            self.set_audio_level(0.0)
            state_manager.set_state(SystemState.IDLE, "VICTOR IS STANDING BY")

        threading.Thread(target=speak_worker, daemon=True).start()

    @Slot(str, str)
    def executeAction(self, action_name: str, target: str):
        """Execute a computer control action directly from UI."""
        self.log("ACTION", f"Executing {action_name} ({target})...", "INFO")

        if action_name == "open_app":
            ok, msg = computer.open_application(target)
            self.log("ACTION", msg, "OK" if ok else "WARN")
            if ok:
                tts_engine.speak(f"Opening {target}.", blocking=False)

        elif action_name == "screenshot":
            ok, msg = computer.take_screenshot()
            self.log("ACTION", msg, "OK" if ok else "WARN")
            if ok:
                play_sound("acknowledge")
                tts_engine.speak("Screenshot captured.", blocking=False)

        elif action_name == "volume":
            try:
                ok, msg = computer.set_volume(int(target))
                self.log("ACTION", msg, "OK" if ok else "WARN")
            except Exception:
                pass

        elif action_name == "media":
            ok, msg = computer.media_control(target)
            self.log("ACTION", msg, "OK" if ok else "WARN")

    @Slot()
    def closeApplication(self):
        """Gracefully terminate background services and exit."""
        self.log("CORE", "Shutting down VICTOR subsystems...", "INFO")
        wake_word_service.stop()
        telemetry_service.stop()
        tts_engine.stop()
        speech_recognizer.cancel()
        QGuiApplication.quit()


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("VICTOR")
    app.setOrganizationName("VictorAI")

    backend = VictorBackend()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("victor", backend)

    base_dir = Path(__file__).resolve().parent
    qml_file = base_dir / "qml" / "Main.qml"

    engine.load(str(qml_file))

    if not engine.rootObjects():
        print("[-] VICTOR UI failed to load QML root object.")
        sys.exit(1)

    print("[+] VICTOR Neural Command Interface online!")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
