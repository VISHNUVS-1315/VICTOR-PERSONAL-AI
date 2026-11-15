"""
VICTOR AI - MASTER LAUNCHER
Usage:
    python run_victor.py             # Launches Native JARVIS Desktop UI (PySide6 / QML)
    python run_victor.py --voice     # Launches Hands-Free Voice Chat Console
    python run_victor.py --train     # Re-trains custom 'Victor' wake-word model
    python run_victor.py --test      # Runs comprehensive test suite
    python run_victor.py --web       # Opens Web Browser Interface fallback
"""

import sys
import os
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def launch_desktop_ui():
    print("=" * 65)
    print("   [+] Launching VICTOR Neural Command Center (PySide6 / QML)...")
    print("=" * 65)
    from src.ui.main import main as ui_main
    ui_main()


def launch_voice_chat():
    print("=" * 65)
    print("   [+] Launching VICTOR Hands-Free Voice Console...")
    print("=" * 65)
    from src.voice.wake_word import wake_word_service
    from src.voice.stt import listen
    from src.voice.tts import speak
    from src.brain.llm import victor_brain

    speak("Victor neural system online. Standing by for voice input.")
    while True:
        try:
            user_text = listen()
            if not user_text:
                continue
            if user_text.lower().strip() in ("exit", "stop", "goodbye", "quit"):
                speak("Deactivating system. Goodbye.")
                break
            print(f"\nYou: {user_text}")
            reply = victor_brain.query(user_text)
            print(f"Victor: {reply}\n")
            speak(reply)
        except KeyboardInterrupt:
            print("\nVoice console stopped.")
            break


def launch_web_ui():
    web_file = ROOT_DIR / "src" / "ui" / "web" / "index.html"
    print("=" * 65)
    print(f"   [+] Opening VICTOR Web UI in default browser...")
    print(f"   File: {web_file}")
    print("=" * 65)
    webbrowser.open(web_file.as_uri())


def run_tests():
    import unittest
    from tests.test_victor import TestVictorSubsystems
    suite = unittest.TestLoader().loadTestsFromTestCase(TestVictorSubsystems)
    unittest.TextTestRunner(verbosity=2).run(suite)


def run_training():
    from scripts.train_victor_model import train_victor_model
    train_victor_model()


if __name__ == "__main__":
    args = [a.lower() for a in sys.argv[1:]]

    if "--voice" in args or "-v" in args:
        launch_voice_chat()
    elif "--train" in args:
        run_training()
    elif "--test" in args or "-t" in args:
        run_tests()
    elif "--web" in args or "-w" in args or "web" in args:
        launch_web_ui()
    else:
        try:
            launch_desktop_ui()
        except ImportError as e:
            print(f"PySide6 desktop launch encountered an issue: {e}")
            print("Falling back to opening the VICTOR Web Interface...")
            launch_web_ui()
