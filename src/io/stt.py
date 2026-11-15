"""
Legacy bridge to modern voice stt module
"""
from src.voice.stt import SpeechRecognizer, speech_recognizer, listen

__all__ = ["SpeechRecognizer", "speech_recognizer", "listen"]

if __name__ == "__main__":
    print("Testing speech recognition...")
    print("Recognized:", listen())
