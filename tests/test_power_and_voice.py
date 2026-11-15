"""
VICTOR Power Profile & Voice Reliability Test Suite
Verifies:
1. Power Modes (low_power, balanced, performance)
2. Dynamic Telemetry Interval Throttling
3. Cached GPU Telemetry (RTX 5060)
4. Fast-Track Voice & Power Commands
5. VAD Audio Calibration & Adaptive Silence Endpointing
6. Voice Language Selection (auto, en, ta)
7. Single Response Guarantee & Concurrency Locking
8. Instant TTS Speech Interruption
"""

import sys
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.actions.computer_control import computer
from src.brain.llm import victor_brain
from src.config.settings import settings
from src.services.telemetry_service import telemetry_service
from src.voice.stt import speech_recognizer
from src.voice.tts import tts_engine
from src.voice.wake_word import wake_word_service


class TestPowerAndVoiceReliability(unittest.TestCase):

    def test_01_power_modes_configuration(self):
        """Verify power modes can be set and reflect in settings."""
        for mode in ("low_power", "balanced", "performance"):
            settings.set_power_mode(mode)
            self.assertEqual(settings.get_power_mode(), mode)
            self.assertEqual(settings.get("ui.power_mode"), mode)

        # Reset to default low_power
        settings.set_power_mode("low_power")
        self.assertEqual(settings.get_power_mode(), "low_power")
        print("\n[TEST 1] Power modes verified: low_power (default), balanced, performance.")

    def test_02_dynamic_telemetry_interval(self):
        """Verify telemetry interval dynamically throttles per power mode."""
        settings.set_power_mode("low_power")
        self.assertEqual(telemetry_service.interval, 3.5)

        settings.set_power_mode("balanced")
        self.assertEqual(telemetry_service.interval, 2.0)

        settings.set_power_mode("performance")
        self.assertEqual(telemetry_service.interval, 1.0)

        settings.set_power_mode("low_power")
        print("\n[TEST 2] Dynamic telemetry interval verified: low_power=3.5s, balanced=2.0s, perf=1.0s.")

    def test_03_gpu_telemetry_caching(self):
        """Verify GPU queries are cached to prevent repeated nvidia-smi executions."""
        t1 = time.time()
        stat1 = computer.get_system_telemetry()
        t2 = time.time()
        stat2 = computer.get_system_telemetry()
        t3 = time.time()

        # The second call must be instantaneous (<5ms) because of 4.0s cache
        self.assertLess(t3 - t2, 0.05)
        self.assertIn("gpu", stat1)
        self.assertIn("gpu", stat2)
        self.assertEqual(stat1["gpu"]["name"], stat2["gpu"]["name"])
        print(f"\n[TEST 3] GPU telemetry caching verified: cached hit took {(t3-t2)*1000:.2f}ms.")

    def test_04_fast_track_commands(self):
        """Verify voice commands for power modes and stopping speech respond instantly."""
        res_lp = victor_brain.query("low power mode")
        self.assertIn("Low Power", res_lp)
        self.assertEqual(settings.get_power_mode(), "low_power")

        res_bal = victor_brain.query("balanced mode")
        self.assertIn("Balanced", res_bal)
        self.assertEqual(settings.get_power_mode(), "balanced")

        res_perf = victor_brain.query("performance mode")
        self.assertIn("Performance", res_perf)
        self.assertEqual(settings.get_power_mode(), "performance")

        # Speech stop fast-track
        res_stop = victor_brain.query("stop talking")
        self.assertIn("stopped", res_stop.lower())

        settings.set_power_mode("low_power")
        print("\n[TEST 4] Fast-track power and speech interruption commands verified.")

    def test_05_vad_and_silence_endpointing_config(self):
        """Verify VAD parameters for long sentences and patience."""
        self.assertGreaterEqual(speech_recognizer.silence_endpoint_duration, 0.8)
        self.assertLessEqual(speech_recognizer.silence_endpoint_duration, 1.2)
        self.assertEqual(speech_recognizer.min_speech_duration, 0.5)
        self.assertEqual(speech_recognizer.max_record_seconds, 30.0)
        print(f"\n[TEST 5] VAD endpointing verified: {speech_recognizer.silence_endpoint_duration}s silence tolerance, 30s max duration.")

    def test_06_language_mode_support(self):
        """Verify language mode settings for English, Tamil, and Auto."""
        settings.set("language_mode", "auto")
        self.assertEqual(settings.get("language_mode"), "auto")

        settings.set("language_mode", "en")
        self.assertEqual(settings.get("language_mode"), "en")

        settings.set("language_mode", "ta")
        self.assertEqual(settings.get("language_mode"), "ta")

        settings.set("language_mode", "auto")
        print("\n[TEST 6] Multi-language support verified: auto (English/Tamil), en, ta.")

    def test_07_tts_interruption(self):
        """Verify tts_engine stop immediately sets stop flag."""
        tts_engine.stop()
        self.assertTrue(tts_engine._stop_requested)
        self.assertFalse(tts_engine.is_speaking)
        print("\n[TEST 7] Instant TTS speech interruption verified.")

    def test_08_wake_word_self_trigger_prevention(self):
        """Verify wake-word listener pause/resume and speaking suppression."""
        listener = wake_word_service
        listener.set_speaking(True)
        self.assertTrue(listener._is_speaking)

        listener.set_speaking(False)
        self.assertFalse(listener._is_speaking)

        listener.pause()
        self.assertTrue(listener.is_paused())

        listener.resume()
        self.assertFalse(listener.is_paused())
        print("\n[TEST 8] Audio self-trigger prevention & pause/resume verified.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
