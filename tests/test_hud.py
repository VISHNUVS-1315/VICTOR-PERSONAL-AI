"""
Headless tests for the VICTOR HUD conversation loop.

Audio hardware, Whisper and Ollama are replaced with scripted fakes so the
state machine can be verified deterministically:

* listen -> think -> speak -> listen without re-activation
* interruption returns to listening and keeps the session alive
* a second activated session is ignored while one is running
* the wake word service is paused while the microphone is held
"""

import os
import sys
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QGuiApplication  # noqa: E402

_APP = QGuiApplication.instance() or QGuiApplication(sys.argv)


class FakeSpeech:
    """Scripted stand-in for SpeechRecognizer."""

    def __init__(self, utterances):
        self.utterances = list(utterances)
        self.calls = 0
        self.paused = False

    def listen_and_transcribe(self, energy_callback=None, language=None, on_transcribe=None):
        self.calls += 1
        if energy_callback:
            energy_callback(0.4)
        if on_transcribe:
            on_transcribe()
        if self.utterances:
            return self.utterances.pop(0), "en"
        time.sleep(0.05)
        return "", "timeout"

    def cancel(self):
        pass

    def is_model_loaded(self):
        return True

    def unload_model(self):
        pass


class FakeBrain:
    def __init__(self):
        self.queries = []

    def query(self, text):
        self.queries.append(text)
        time.sleep(0.05)
        return f"Answer {len(self.queries)}."


class FakeTTS:
    def __init__(self, speak_seconds=0.25):
        self.spoken = []
        self._is_speaking = False
        self._stopped = False
        self.speak_seconds = speak_seconds
        self.interrupted = False

    @property
    def is_speaking(self):
        return self._is_speaking

    def speak(self, text, blocking=True, energy_callback=None):
        self.spoken.append(text)
        self._is_speaking = True
        self._stopped = False
        deadline = time.time() + self.speak_seconds
        while time.time() < deadline and not self._stopped:
            if energy_callback:
                energy_callback(0.6)
            time.sleep(0.02)
        self._is_speaking = False
        if energy_callback:
            energy_callback(0.0)

    def stop(self):
        self.interrupted = True
        self._stopped = True
        self._is_speaking = False


class FakeWakeWord:
    def __init__(self):
        self.pauses = 0
        self.resumes = 0
        self.on_detected = None

    def pause(self):
        self.pauses += 1

    def resume(self):
        self.resumes += 1

    def start(self):
        pass

    def stop(self):
        pass


class HudLoopTests(unittest.TestCase):
    def setUp(self):
        import src.ui.hud as hud

        self.hud = hud
        self._saved = (hud.speech_recognizer, hud.victor_brain, hud.tts_engine, hud.wake_word_service)
        self.stt = FakeSpeech(["Hello Victor", "And a second question"])
        self.brain = FakeBrain()
        self.tts = FakeTTS()
        self.wake = FakeWakeWord()
        hud.speech_recognizer = self.stt
        hud.victor_brain = self.brain
        hud.tts_engine = self.tts
        hud.wake_word_service = self.wake
        self.backend = hud.VictorHudBackend(qa_mode=True)

    def tearDown(self):
        (
            self.hud.speech_recognizer,
            self.hud.victor_brain,
            self.hud.tts_engine,
            self.hud.wake_word_service,
        ) = self._saved
        self.backend._server.close()

    def _wait(self, predicate, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            _APP.processEvents()      # deliver queued signals from the worker thread
            if predicate():
                return True
            time.sleep(0.02)
        return False

    def test_conversation_continues_without_reactivation(self):
        self.backend.start_session()
        self.assertTrue(self._wait(lambda: not self.backend._session_active, timeout=6.0))
        self.assertEqual(self.brain.queries, ["Hello Victor", "And a second question"])
        self.assertEqual(self.tts.spoken, ["Answer 1.", "Answer 2."])
        self.assertEqual(self.stt.calls, 3)          # two turns + closing listen
        self.assertGreaterEqual(self.wake.pauses, 2)  # mic handed over per turn
        self.assertGreaterEqual(self.wake.resumes, 1)

    def test_interrupting_speech_keeps_session_alive(self):
        self.backend.start_session()
        self.assertTrue(self._wait(lambda: self.tts.is_speaking))
        self.backend.interrupt()
        self.assertTrue(self.tts.interrupted)
        self.assertTrue(
            self._wait(lambda: len(self.tts.spoken) == 2, timeout=5.0),
            "session should continue after an interruption",
        )
        self.assertTrue(self._wait(lambda: not self.backend._session_active, timeout=6.0))
        self.assertEqual(len(self.brain.queries), 2)

    def test_second_activation_is_ignored_while_running(self):
        self.backend.start_session()
        first = self.backend._session_thread
        self._wait(lambda: self.stt.calls >= 1)
        self.backend.start_session()
        self.assertIs(self.backend._session_thread, first)
        self._wait(lambda: not self.backend._session_active, timeout=6.0)
        self.assertEqual(len(self.brain.queries), 2)

    def test_transcribing_state_is_reported(self):
        statuses = []
        self.backend.statusTextChanged.connect(statuses.append)
        self.backend.start_session()
        self._wait(lambda: not self.backend._session_active, timeout=6.0)
        self.assertIn("TRANSCRIBING", statuses)
        self.assertIn("PROCESSING", statuses)
        self.assertIn("SPEAKING", statuses)


if __name__ == "__main__":
    unittest.main()
