"""
VICTOR Custom Wake-Word Listener Service
Runs continuous, lightweight, offline background audio listener detecting the exact wake word "Victor".
Includes self-speech suppression (TTS active guard), sensitivity adjustment, pause/resume,
audio feedback chime, and event dispatching.
"""

import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional

# Limit thread pool to 1 thread per session for lightweight background listening
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

from src.config.settings import DATA_DIR, settings
from src.core.audio_effects import play_sound
from src.core.state import state_manager, SystemState

# Path to the custom trained Victor ONNX model
VICTOR_MODEL_PATH = DATA_DIR / "models" / "victor.onnx"
SAMPLE_RATE = 16000
BLOCK_SIZE = 1280  # 80ms chunk for openWakeWord


class WakeWordListener:
    """Offline background audio listener for 'Victor'."""

    def __init__(self, on_detected: Optional[Callable[[], None]] = None):
        self.on_detected = on_detected
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._model: Optional[Model] = None
        self._lock = threading.Lock()
        
        # Guard against self-triggering while TTS is speaking
        self._is_speaking = False
        
        # False-trigger prevention cooldown
        self._last_trigger_time = 0.0
        self._cooldown_seconds = 2.0
        
        # Audio device selection
        self.mic_index = settings.get("voice.mic_index", None)
        self.sensitivity = float(settings.get("voice.wake_word_sensitivity", 0.5))

    def set_speaking(self, speaking: bool):
        """Notify listener whether Victor is currently speaking to suppress self-activation."""
        self._is_speaking = bool(speaking)

    def set_sensitivity(self, val: float):
        """Update detection sensitivity threshold (0.1 to 0.95)."""
        self.sensitivity = max(0.1, min(0.95, float(val)))

    def pause(self):
        """Temporarily pause wake word listening without killing background thread."""
        self._paused = True

    def resume(self):
        """Resume wake word listening."""
        self._paused = False

    def is_paused(self) -> bool:
        return self._paused

    def is_running(self) -> bool:
        return self._running

    def trigger_manually(self):
        """Simulate wake word trigger manually (e.g. from UI button)."""
        self._on_wake_trigger("manual")

    def _on_wake_trigger(self, source: str = "acoustic"):
        now = time.time()
        if now - self._last_trigger_time < self._cooldown_seconds:
            return
        self._last_trigger_time = now

        # Immediately pause wake-word listener to yield microphone to STT
        self.pause()

        # Play futuristic activation sound
        play_sound("activation")

        # Set UI state to LISTENING
        state_manager.set_state(SystemState.LISTENING, "VICTOR IS LISTENING...")

        # Fire callback
        if self.on_detected:
            try:
                self.on_detected()
            except Exception as e:
                print(f"[!] Error in wake word callback: {e}")

    def _load_model(self):
        if not VICTOR_MODEL_PATH.exists():
            print(f"[!] Custom model {VICTOR_MODEL_PATH} not found. Running training...")
            from scripts.train_victor_model import train_victor_model
            train_victor_model()

        print(f"[+] Loading Victor custom wake word model from {VICTOR_MODEL_PATH}...")
        
        # Optimize ONNX runtime thread pool to avoid spawning 30+ threads on 16-core CPU
        import onnxruntime as ort
        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = 1
        sess_opts.inter_op_num_threads = 1
        sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        self._model = Model(
            wakeword_models=[str(VICTOR_MODEL_PATH)],
            vad_threshold=0.5,
            inference_framework="onnx"
        )
        print("[+] Wake-word engine initialized successfully with Silero VAD pre-filter.")

    def _worker(self):
        try:
            self._load_model()
        except Exception as e:
            print(f"[-] Failed to initialize wake word model: {e}")
            self._running = False
            return

        print(f"[+] Victor is listening for 'Victor' in background (Threshold: {self.sensitivity})...")

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                device=self.mic_index,
                blocksize=BLOCK_SIZE
            ) as stream:
                while self._running:
                    if self._paused or self._is_speaking:
                        # Sleep to keep CPU at 0% while user speaks or Victor answers
                        time.sleep(0.15)
                        continue

                    try:
                        audio, overflowed = stream.read(BLOCK_SIZE)
                    except Exception:
                        time.sleep(0.1)
                        continue

                    audio = np.squeeze(audio)

                    # Predict wake word score
                    try:
                        prediction = self._model.predict(audio)
                        score = prediction.get("victor", 0.0)

                        if score >= self.sensitivity:
                            print(f"\n[+] WAKE WORD DETECTED: 'Victor' (Score: {score:.3f})")
                            self._on_wake_trigger("model")
                    except Exception as pred_err:
                        # Reset preprocessor buffers on glitch
                        time.sleep(0.05)

        except Exception as stream_err:
            print(f"[-] Wake-word audio stream error: {stream_err}")
            self._running = False

    def start(self):
        """Start wake word listener in a dedicated background daemon thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._paused = False
            self._thread = threading.Thread(target=self._worker, daemon=True, name="VictorWakeWordThread")
            self._thread.start()

    def stop(self):
        """Stop wake word listener thread."""
        with self._lock:
            self._running = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.5)
            self._thread = None
            print("[+] Wake-word listener stopped.")


# Global instance
wake_word_service = WakeWordListener()

