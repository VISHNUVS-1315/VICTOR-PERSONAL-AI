"""
Test wake word detection accuracy on various test phrases.
"""

import sys
import tempfile
import wave
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pyttsx3
from scipy import signal
from openwakeword.model import Model

def synthesize_clip(text: str, voice_id: str, rate: int = 160) -> np.ndarray:
    engine = pyttsx3.init()
    engine.setProperty("voice", voice_id)
    engine.setProperty("rate", rate)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_name = f.name
    engine.save_to_file(text, tmp_name)
    engine.runAndWait()
    engine.stop()

    with wave.open(tmp_name, "rb") as wf:
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    Path(tmp_name).unlink(missing_ok=True)

    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if sr != 16000:
        audio = signal.resample(audio, int(len(audio) * 16000 / sr))
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)

def test_phrases():
    model = Model(
        wakeword_models=[str(ROOT_DIR / "data" / "models" / "victor.onnx")],
        vad_threshold=0.5,
        inference_framework="onnx"
    )

    engine = pyttsx3.init()
    voices = [v.id for v in engine.getProperty("voices")]
    engine.stop()

    test_words = [
        ("Victor", True),
        ("Hey Victor", True),
        ("Victor please", True),
        ("Hey Jarvis", False),
        ("Alexa", False),
        ("Computer", False),
        ("Testing microphone", False),
        ("Good morning Vishnu", False)
    ]

    print("Evaluating custom Victor detector:")
    for phrase, is_target in test_words:
        audio = synthesize_clip(phrase, voices[0], rate=165)
        # Pad with 0.5s silence before and after
        silence = np.zeros(8000, dtype=np.int16)
        full_audio = np.concatenate([silence, audio, silence])
        
        # Reset model buffers
        model.reset()
        peak_score = 0.0
        for i in range(0, len(full_audio) - 1280, 1280):
            chunk = full_audio[i:i + 1280]
            pred = model.predict(chunk)
            score = pred.get("victor", 0.0)
            if score > peak_score:
                peak_score = score

        status = "EXPECTED POSITIVE" if is_target else "EXPECTED NEGATIVE"
        triggered = peak_score >= 0.5
        correct = (triggered == is_target)
        mark = "PASS" if correct else "FAIL"
        print(f"  [{mark}] '{phrase}' ({status}) -> Peak Score: {peak_score:.4f} (Triggered: {triggered})")

if __name__ == "__main__":
    test_phrases()

