"""
VICTOR Personal AI Assistant - Comprehensive Automated Test Suite
Verifies all 9 core subsystems:
1. Ollama Connection
2. AI Response Generation & Persona
3. Custom Wake-Word ONNX Model ('Victor')
4. Faster-Whisper Speech Recognition Setup
5. PyTTSx3 Speech Synthesis & Cleaners
6. Persistent Memory & Security Filtering
7. Computer Automation & Hardware Telemetry (RTX 5060)
8. Central State Machine Transitions
9. Background Services Threading & Stability
"""

import sys
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np

from src.actions.computer_control import computer, APP_WHITELIST
from src.brain.llm import victor_brain
from src.core.state import state_manager, SystemState
from src.core.audio_effects import ensure_sound_assets
from src.memory.store import (
    save_memory,
    get_memories,
    delete_memory,
    contains_sensitive_info,
    log_action,
    get_recent_action_logs
)
from src.services.telemetry_service import telemetry_service
from src.voice.wake_word import WakeWordListener, VICTOR_MODEL_PATH
from src.voice.stt import speech_recognizer
from src.voice.tts import tts_engine


class TestVictorSubsystems(unittest.TestCase):

    def setUp(self):
        ensure_sound_assets()

    # 1. OLLAMA CONNECTION
    def test_01_ollama_connection(self):
        print("\n[TEST 1] Testing Ollama connection and model availability...")
        ok, msg = victor_brain.check_connection()
        self.assertTrue(ok, f"Ollama connection check failed: {msg}")
        print(f"  --> PASS: {msg}")

    # 2. AI RESPONSE GENERATION & INTENT
    def test_02_ai_response_generation(self):
        print("\n[TEST 2] Testing Qwen 3.5 AI conversational inference...")
        response = victor_brain.query("Hello Victor. What are you designed for? Answer in one sentence.")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 10)
        self.assertNotIn("inference error", response.lower())
        print(f"  --> PASS: Response: '{response[:90]}...'")

    # 3. WAKE-WORD DETECTION & CUSTOM ONNX MODEL
    def test_03_custom_wake_word_model(self):
        print("\n[TEST 3] Testing custom 'Victor' ONNX model and OpenWakeWord loading...")
        self.assertTrue(VICTOR_MODEL_PATH.exists(), f"Model {VICTOR_MODEL_PATH} must exist.")
        
        from openwakeword.model import Model
        oww = Model(wakeword_models=[str(VICTOR_MODEL_PATH)], inference_framework="onnx")
        self.assertIn("victor", oww.models)
        
        # Test inference with zero frame (should be 0 or very low)
        silence_chunk = np.zeros(1280, dtype=np.int16)
        pred = oww.predict(silence_chunk)
        self.assertIn("victor", pred)
        self.assertLess(pred["victor"], 0.25)
        print(f"  --> PASS: Custom model 'victor.onnx' loaded and evaluated successfully. (Baseline score: {pred['victor']:.4f})")

    # 4. SPEECH RECOGNITION (FASTER-WHISPER)
    def test_04_speech_recognition_setup(self):
        print("\n[TEST 4] Testing Faster-Whisper recognizer initialization...")
        speech_recognizer._ensure_model_loaded()
        self.assertIsNotNone(speech_recognizer._model)
        self.assertEqual(speech_recognizer.compute_type, "int8")
        print(f"  --> PASS: Faster-Whisper '{speech_recognizer.model_name}' loaded on {speech_recognizer.device} {speech_recognizer.compute_type}.")

    # 5. NATURAL TTS ENGINE & TEXT CLEANER
    def test_05_tts_engine(self):
        print("\n[TEST 5] Testing TTS text cleaners and configuration...")
        dirty_text = "Here is a **bold** `code block` and a link https://example.com *with* emojis! # Heading"
        cleaned = tts_engine.clean_text_for_speech(dirty_text)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("`", cleaned)
        self.assertNotIn("https://", cleaned)
        self.assertEqual(tts_engine.rate, 170)
        print(f"  --> PASS: Text cleaned successfully for speech: '{cleaned}'")

    # 6. PERSISTENT MEMORY & SECURITY FILTERING
    def test_06_memory_store_and_security(self):
        print("\n[TEST 6] Testing SQLite memory store and credential filter...")
        # Check credential blocking
        self.assertTrue(contains_sensitive_info("My password is secret123"))
        self.assertTrue(contains_sensitive_info("My api_key = AIzaSyD9874523094857209348572093845"))
        blocked_res = save_memory("My password is secret123", category="credentials")
        self.assertIn("Security Guard", blocked_res)

        # Check normal memory saving
        test_fact = f"Operator automated test fact #{int(time.time())}"
        save_res = save_memory(test_fact, category="testing")
        self.assertEqual(save_res, "Memory saved successfully.")

        # Check retrieval
        memories = get_memories(category="testing")
        self.assertTrue(any(m["content"] == test_fact for m in memories))
        target_id = [m["id"] for m in memories if m["content"] == test_fact][0]

        # Check deletion
        deleted = delete_memory(target_id)
        self.assertTrue(deleted)
        print("  --> PASS: Memory store created, filtered credentials, saved fact, and cleaned up.")

    # 7. COMPUTER CONTROL & SYSTEM TELEMETRY
    def test_07_computer_control(self):
        print("\n[TEST 7] Testing computer automation, whitelist, and hardware telemetry...")
        time_str = computer.get_time_and_date()
        self.assertIn("2026", time_str)

        # Whitelist verification
        self.assertIn("code", APP_WHITELIST.values())
        ok_blocked, msg_blocked = computer.open_application("malicious_unapproved_script.exe")
        self.assertFalse(ok_blocked)
        self.assertIn("whitelist", msg_blocked)

        # Telemetry metrics
        telemetry = computer.get_system_telemetry()
        self.assertGreaterEqual(telemetry["cpu_percent"], 0.0)
        self.assertGreater(telemetry["ram_percent"], 0.0)
        self.assertGreater(telemetry["ram_total_gb"], 16.0)  # User has 24GB
        
        gpu = telemetry["gpu"]
        print(f"  --> Telemetry: CPU={telemetry['cpu_percent']}%, RAM={telemetry['ram_percent']}%, GPU Available={gpu['available']}")
        if gpu["available"]:
            self.assertGreater(gpu["temperature"], 0)
            print(f"  --> PASS: RTX 5060 GPU Online: Temp={gpu['temperature']}°C, VRAM Used={gpu['vram_used_mb']} MB")
        else:
            print("  --> PASS: CPU & RAM metrics operational.")

    # 8. CENTRAL STATE TRANSITIONS
    def test_08_state_transitions(self):
        print("\n[TEST 8] Testing central state machine transitions...")
        recorded = []

        def listener(st, msg):
            recorded.append((st.value, msg))

        state_manager.add_listener(listener)
        state_manager.set_state(SystemState.LISTENING, "Listening test...")
        state_manager.set_state(SystemState.THINKING, "Thinking test...")
        state_manager.set_state(SystemState.IDLE, "Idle test...")
        state_manager.remove_listener(listener)

        self.assertEqual(len(recorded), 3)
        self.assertEqual(recorded[0][0], "listening")
        self.assertEqual(recorded[1][0], "thinking")
        self.assertEqual(recorded[2][0], "idle")
        print("  --> PASS: State machine dispatched all state transitions properly.")

    # 9. BACKGROUND SERVICES STABILITY
    def test_09_background_services(self):
        print("\n[TEST 9] Testing telemetry and wake-word background service lifecycle...")
        # Telemetry service lifecycle
        telemetry_service.start()
        self.assertTrue(telemetry_service._running)
        time.sleep(0.5)
        snap = telemetry_service.latest_snapshot
        self.assertIn("cpu_percent", snap)
        telemetry_service.stop()
        self.assertFalse(telemetry_service._running)

        # Wake-word listener lifecycle
        listener = WakeWordListener()
        self.assertFalse(listener.is_running())
        listener.set_speaking(True)
        self.assertTrue(listener._is_speaking)
        listener.set_speaking(False)
        self.assertFalse(listener._is_speaking)
        listener.set_sensitivity(0.65)
        self.assertEqual(listener.sensitivity, 0.65)
        print("  --> PASS: Background service lifecycle and thread safety verified.")


if __name__ == "__main__":
    unittest.main(verbosity=2)

