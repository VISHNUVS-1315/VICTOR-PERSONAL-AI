"""
Legacy bridge to modern wake word module
"""
from src.voice.wake_word import WakeWordListener, wake_word_service

__all__ = ["WakeWordListener", "wake_word_service"]

if __name__ == "__main__":
    print("Starting wake word listener...")
    wake_word_service.on_detected = lambda: print("[+] WAKE WORD DETECTED: Victor!")
    wake_word_service.start()
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        wake_word_service.stop()
