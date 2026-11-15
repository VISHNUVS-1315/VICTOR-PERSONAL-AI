"""
VICTOR Speech-to-Text (STT) Recognition Service
Powered by Faster-Whisper with INT8 quantization.
Includes:
- Dynamic ambient noise floor calibration
- 1.0-second pre-speech circular ring buffer
- Adaptive VAD silence endpointing (800–1200ms pause tolerance)
- Minimum speech duration filter (prevents processing clicks/coughs)
- Support for long, multi-clause sentences (up to 30s)
- Lazy loading and idle memory management
"""

import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, Optional, Tuple

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from src.config.settings import settings

SAMPLE_RATE = 16000
BLOCK_SIZE = 1600  # 100ms chunk at 16kHz


class SpeechRecognizer:
    def __init__(self):
        self._model: Optional[WhisperModel] = None
        self._lock = threading.Lock()
        self._is_listening = False
        self._stop_requested = False
        self._last_used_time = 0.0

        # Parameters from settings
        self.mic_index = settings.get("voice.mic_index", None)
        self.silence_endpoint_duration = float(settings.get("voice.silence_duration", 1.0))
        self.min_speech_duration = float(settings.get("voice.min_speech_duration", 0.5))
        self.max_record_seconds = float(settings.get("voice.max_record_seconds", 30.0))
        self.max_wait_seconds = 10.0

        # Model settings
        self.model_name = settings.get("voice.stt_model", "small")
        self.device = settings.get("voice.stt_device", "cpu")
        self.compute_type = settings.get("voice.stt_compute_type", "int8")

    def _ensure_model_loaded(self):
        with self._lock:
            if self._model is None:
                print(f"[+] Loading Faster-Whisper model ('{self.model_name}' on {self.device} {self.compute_type})...")
                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type
                )
                print("[+] Faster-Whisper speech recognizer ready.")
            self._last_used_time = time.time()

    def unload_model(self):
        """Release Whisper model from memory during low-power standby."""
        with self._lock:
            if self._model is not None:
                self._model = None
                print("[+] Faster-Whisper model unloaded from RAM.")

    def cancel(self):
        """Cancel ongoing audio capture."""
        self._stop_requested = True

    def listen_and_transcribe(
        self,
        energy_callback: Optional[Callable[[float], None]] = None,
        language: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Record voice patiently until sentence is complete.
        Returns: (transcribed_text, detected_language)
        """
        self._ensure_model_loaded()
        self._is_listening = True
        self._stop_requested = False

        audio_chunks = []
        # Pre-speech buffer: 10 chunks of 100ms = 1.0s audio buffer
        previous_chunks = deque(maxlen=10)

        speech_started = False
        silence_time = 0.0
        start_wait = time.monotonic()
        recording_start = 0.0

        # Measure ambient noise during first 3 chunks (300ms)
        ambient_samples = []
        noise_calibrated = False
        speech_thresh = 0.012
        silence_thresh = 0.008

        print("[*] Victor listening patiently for user speech...")

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                device=self.mic_index,
                blocksize=BLOCK_SIZE
            ) as stream:
                while not self._stop_requested:
                    chunk, overflowed = stream.read(BLOCK_SIZE)
                    chunk = chunk.copy()

                    # Calculate RMS audio energy
                    rms = float(np.sqrt(np.mean(chunk ** 2)))
                    chunk_dur = len(chunk) / SAMPLE_RATE

                    # Calibrate ambient noise floor
                    if not noise_calibrated:
                        ambient_samples.append(rms)
                        if len(ambient_samples) >= 3:
                            noise_floor = float(np.mean(ambient_samples))
                            speech_thresh = max(0.007, noise_floor * 2.2 + 0.004)
                            silence_thresh = max(0.004, noise_floor * 1.35 + 0.001)
                            noise_calibrated = True

                    # Emit energy level for UI visualizer
                    if energy_callback:
                        boosted_level = min(1.0, rms * 16.0)
                        try:
                            energy_callback(boosted_level)
                        except Exception:
                            pass

                    # 1. STANDBY WAITING FOR SPEECH
                    if not speech_started:
                        previous_chunks.append(chunk)

                        if rms >= speech_thresh:
                            speech_started = True
                            recording_start = time.monotonic()
                            audio_chunks.extend(previous_chunks)
                            previous_chunks.clear()
                            print("[*] User speech onset detected. Recording sentence...")

                        elif time.monotonic() - start_wait > self.max_wait_seconds:
                            print("[*] Speech capture timed out (no voice detected).")
                            return "", "timeout"

                    # 2. ACTIVELY RECORDING SPEECH
                    else:
                        audio_chunks.append(chunk)
                        total_speech_time = time.monotonic() - recording_start

                        # Voice activity check
                        if rms < silence_thresh:
                            silence_time += chunk_dur
                        else:
                            silence_time = 0.0

                        # Adaptive pause tolerance:
                        # If user just started speaking (<1.8s), give more time (1.2s) to formulate thought.
                        # If sentence has substantial content (>2.0s), 1.0s silence marks sentence end.
                        active_silence_limit = 1.2 if total_speech_time < 1.8 else self.silence_endpoint_duration

                        # Check for natural sentence completion pause
                        if silence_time >= active_silence_limit:
                            # Filter out momentary clicks / noises
                            if total_speech_time - silence_time < self.min_speech_duration:
                                print("[*] Discarding brief sound spike (<0.5s click/breath). Resetting...")
                                speech_started = False
                                audio_chunks.clear()
                                silence_time = 0.0
                                start_wait = time.monotonic()
                                continue
                            print(f"[*] Natural pause detected ({silence_time:.1f}s silence). Finalizing sentence...")
                            break

                        # Max safety timeout for long sentence
                        if total_speech_time >= self.max_record_seconds:
                            print("[*] Max recording limit reached (30s). Finalizing...")
                            break

        except Exception as err:
            print(f"[-] Microphone audio stream error: {err}")
            return "", "error"
        finally:
            self._is_listening = False
            if energy_callback:
                try:
                    energy_callback(0.0)
                except Exception:
                    pass

        if not audio_chunks or self._stop_requested:
            return "", "cancelled"

        # Concatenate audio
        audio = np.concatenate(audio_chunks).squeeze()

        # Check total active audio duration
        duration_sec = len(audio) / SAMPLE_RATE
        if duration_sec < self.min_speech_duration:
            print(f"[*] Audio too short ({duration_sec:.2f}s). Ignored.")
            return "", "incomplete"

        # Transcribe with Faster-Whisper
        print(f"[*] Transcribing {duration_sec:.1f}s of speech with Faster-Whisper...")
        try:
            segments, info = self._model.transcribe(
                audio,
                beam_size=5,
                vad_filter=True,  # Filter out silence at beginning and end
                vad_parameters=dict(min_silence_duration_ms=400),
                language=language
            )

            text = " ".join(seg.text.strip() for seg in segments).strip()
            detected_lang = info.language or "en"

            # Check if empty
            if not text:
                print("[-] Whisper produced empty transcript.")
                return "", "empty"

            print(f"[+] Recognized [{detected_lang.upper()}]: '{text}'")
            return text, detected_lang

        except Exception as tr_err:
            print(f"[-] Whisper transcription failed: {tr_err}")
            return "", "error"


# Global instance
speech_recognizer = SpeechRecognizer()


def listen(energy_callback: Optional[Callable[[float], None]] = None) -> str:
    """Convenience function returning transcribed string."""
    text, _ = speech_recognizer.listen_and_transcribe(energy_callback=energy_callback)
    return text
