"""
VICTOR AI - MASTER LAUNCHER
Usage:
    python run_victor.py             # Launches the animated VICTOR HUD (PySide6 / QML)
    python run_victor.py --hud       # Same as default: animated HUD with continuous voice
    python run_victor.py --classic   # Legacy multi-panel command center UI
    python run_victor.py --tray      # Legacy tray-only mode (no window)
    python run_victor.py --voice     # Hands-free voice console in the terminal
    python run_victor.py --capture DIR  # Render HUD screenshots of each state (QA)
    python run_victor.py --train     # Re-trains custom 'Victor' wake-word model
    python run_victor.py --test      # Runs comprehensive test suite
    python run_victor.py --web       # Opens Web Browser Interface fallback
    python run_victor.py --install-autostart    # Start VICTOR HUD with Windows
    python run_victor.py --remove-autostart     # Stop starting automatically
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


def launch_hud():
    """Primary experience: animated HUD with continuous voice conversation."""
    print("=" * 65)
    print("   [+] Launching VICTOR HUD...")
    print("   [*] Ctrl+Alt+V talk | Ctrl+Alt+X interrupt | Esc interrupt")
    print("=" * 65)
    from src.ui.hud import main as hud_main

    capture = ""
    if "--capture" in sys.argv:
        idx = sys.argv.index("--capture")
        if idx + 1 < len(sys.argv):
            capture = sys.argv[idx + 1]
    return hud_main(capture_path=capture)


def launch_classic():
    print("=" * 65)
    print("   [+] Launching VICTOR Classic Command Center (legacy UI)...")
    print("=" * 65)
    from src.ui.main_legacy import main as classic_main
    classic_main()


def launch_tray():
    print("=" * 65)
    print("   [+] Launching VICTOR Tray Assistant (no window)...")
    print("   [*] Ctrl+Alt+V talk | Ctrl+Alt+T type | Ctrl+Alt+X stop")
    print("=" * 65)
    from src.ui.tray import run_tray
    return run_tray(selftest=("--selftest" in sys.argv), verbose=("--verbose" in sys.argv))


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
    elif "--classic" in args:
        launch_classic()
    elif "--tray" in args or "-r" in args:
        raise SystemExit(launch_tray() or 0)
    elif "--hud" in args or "-u" in args:
        raise SystemExit(launch_hud() or 0)
    elif "--install-autostart" in args:
        from scripts.install_autostart import install
        print(f"[+] Autostart installed: {install()}")
    elif "--remove-autostart" in args:
        from scripts.install_autostart import uninstall
        print(f"[+] Autostart removed: {uninstall()}")
    elif "--train" in args:
        run_training()
    elif "--test" in args or "-t" in args:
        run_tests()
    elif "--web" in args or "-w" in args or "web" in args:
        launch_web_ui()
    else:
        raise SystemExit(launch_hud() or 0)
