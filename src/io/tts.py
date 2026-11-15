"""
Legacy bridge to modern voice tts module
"""
from src.voice.tts import TextToSpeech, tts_engine, speak

__all__ = ["TextToSpeech", "tts_engine", "speak"]

if __name__ == "__main__":
    speak("Victor speech synthesis operational.")
