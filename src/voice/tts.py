"""
VICTOR Text-To-Speech (TTS) Voice Synthesis
Uses Microsoft David / Zira SAPI5 voices via PyTTSx3.
Supports speech interruption, voice rate & volume adjustments,
real-time audio energy visualization callbacks, and thread-safe execution.
"""

import math
import re
import threading
import time
from typing import Callable, Optional

import pyttsx3

from src.config.settings import settings


class TextToSpeech:
    def __init__(self):
        self._lock = threading.Lock()
        self._is_speaking = False
        self._stop_requested = False
        self._current_thread: Optional[threading.Thread] = None
        self._engine: Optional[Any] = None

        # Voice parameters from settings
        self.voice_name = settings.get("voice.tts_voice", "david")
        self.rate = int(settings.get("voice.tts_rate", 170))
        self.volume = float(settings.get("voice.tts_volume", 1.0))

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def stop(self):
        """Immediately interrupt and stop ongoing speech."""
        self._stop_requested = True
        self._is_speaking = False
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass

    def clean_text_for_speech(self, text: str) -> str:
        """Strip markdown symbols, URLs, asterisks, backticks, emojis."""
        t = str(text)
        # Remove URLs
        t = re.sub(r"https?://\S+", "", t)
        # Remove code blocks
        t = re.sub(r"```[\s\S]*?```", "code block omitted", t)
        # Remove inline backticks, bold, italic, headings
        t = re.sub(r"[*_#`~>\[\]]", "", t)
        # Replace multiple spaces/newlines
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def speak(
        self,
        text: str,
        on_start: Optional[Callable[[], None]] = None,
        on_end: Optional[Callable[[], None]] = None,
        energy_callback: Optional[Callable[[float], None]] = None,
        blocking: bool = True
    ):
        """
        Synthesize and speak text.
        If blocking=False, executes in a background thread.
        """
        clean_text = self.clean_text_for_speech(text)
        if not clean_text:
            return

        def _run_speech():
            with self._lock:
                self._is_speaking = True
                self._stop_requested = False

            if on_start:
                try:
                    on_start()
                except Exception:
                    pass

            # Inform wake-word service that Victor is speaking to avoid self-trigger
            try:
                from src.voice.wake_word import wake_word_service
                wake_word_service.set_speaking(True)
            except Exception:
                pass

            # Waveform energy simulation thread for UI
            waveform_active = True

            def _waveform_driver():
                start_t = time.time()
                while waveform_active and not self._stop_requested:
                    t = time.time() - start_t
                    # Modulated rhythmic speech energy
                    v = 0.35 + 0.45 * abs(math.sin(t * 8.0)) * (0.8 + 0.2 * math.sin(t * 22.0))
                    if energy_callback:
                        try:
                            energy_callback(float(v))
                        except Exception:
                            pass
                    time.sleep(0.04)
                if energy_callback:
                    try:
                        energy_callback(0.0)
                    except Exception:
                        pass

            wf_thread = threading.Thread(target=_waveform_driver, daemon=True)
            wf_thread.start()

            engine = None
            try:
                engine = pyttsx3.init()
                self._engine = engine
                engine.setProperty("rate", self.rate)
                engine.setProperty("volume", self.volume)

                # Select voice
                voices = engine.getProperty("voices")
                selected_voice_id = None
                for v in voices:
                    if self.voice_name.lower() in v.name.lower():
                        selected_voice_id = v.id
                        break
                if selected_voice_id:
                    engine.setProperty("voice", selected_voice_id)

                engine.say(clean_text)
                engine.runAndWait()

            except Exception as e:
                print(f"[!] TTS synthesis error: {e}")
            finally:
                waveform_active = False
                self._engine = None
                if engine:
                    try:
                        engine.stop()
                    except Exception:
                        pass

                with self._lock:
                    self._is_speaking = False

                # Inform wake-word service that Victor has finished speaking
                try:
                    from src.voice.wake_word import wake_word_service
                    wake_word_service.set_speaking(False)
                except Exception:
                    pass

                if on_end:
                    try:
                        on_end()
                    except Exception:
                        pass

        if blocking:
            _run_speech()
        else:
            t = threading.Thread(target=_run_speech, daemon=True, name="VictorTTSThread")
            self._current_thread = t
            t.start()


# Global instance
tts_engine = TextToSpeech()


def speak(text: str, blocking: bool = True):
    """Convenience function for speech synthesis."""
    tts_engine.speak(text, blocking=blocking)

