"""
VICTOR Audio Effects & Sound System
Generates and plays futuristic sci-fi audio chimes (Activation, Acknowledgment, Sleep).
Uses native Windows multimedia sound playback without blocking.
"""

import math
import struct
import wave
import threading
from pathlib import Path

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

from src.config.settings import SOUNDS_DIR, settings


def _generate_wav(filepath: Path, tones: list, sample_rate: int = 44100):
    """
    Generate a clean sci-fi sine wave audio chime with harmonics and envelope.
    tones: list of tuples: (freq_start, freq_end, duration_sec, amplitude)
    """
    total_frames = int(sum(t[2] for t in tones) * sample_rate)
    samples = []

    for freq_start, freq_end, duration, amp in tones:
        n_frames = int(duration * sample_rate)
        for i in range(n_frames):
            t = i / sample_rate
            progress = i / max(n_frames - 1, 1)
            # Smooth frequency interpolation
            freq = freq_start + (freq_end - freq_start) * (progress ** 0.8)
            # Exponential attack and decay envelope
            envelope = math.sin(math.pi * min(progress * 4.0, 1.0)) * math.exp(-progress * 3.5)
            # Add subtle harmonic overtone (2x frequency)
            val = amp * envelope * (0.75 * math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(4 * math.pi * freq * t))
            samples.append(val)

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        # Convert float samples (-1.0 to 1.0) to 16-bit PCM
        pcm_bytes = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            pcm_val = int(clamped * 32767)
            pcm_bytes.extend(struct.pack("<h", pcm_val))
        wf.writeframes(pcm_bytes)


def ensure_sound_assets():
    """Ensure all default sound effects exist on disk."""
    activation_wav = SOUNDS_DIR / "activation.wav"
    if not activation_wav.exists():
        # JARVIS-style ascending power chime
        _generate_wav(activation_wav, [
            (587.33, 880.0, 0.12, 0.45),
            (880.0, 1318.5, 0.18, 0.55),
            (1318.5, 1760.0, 0.25, 0.40)
        ])

    ack_wav = SOUNDS_DIR / "acknowledge.wav"
    if not ack_wav.exists():
        _generate_wav(ack_wav, [
            (880.0, 1046.5, 0.08, 0.35),
            (1046.5, 1318.5, 0.14, 0.40)
        ])

    sleep_wav = SOUNDS_DIR / "sleep.wav"
    if not sleep_wav.exists():
        _generate_wav(sleep_wav, [
            (1174.66, 783.99, 0.15, 0.40),
            (783.99, 392.0, 0.25, 0.35)
        ])

    alert_wav = SOUNDS_DIR / "alert.wav"
    if not alert_wav.exists():
        _generate_wav(alert_wav, [
            (440.0, 330.0, 0.15, 0.50),
            (330.0, 220.0, 0.25, 0.40)
        ])


def play_sound(sound_name: str):
    """Play a sound effect asynchronously by name ('activation', 'acknowledge', 'sleep', 'alert')."""
    if not settings.get("voice.audio_feedback", True):
        return

    wav_path = SOUNDS_DIR / f"{sound_name}.wav"
    if not wav_path.exists():
        ensure_sound_assets()

    if WINSOUND_AVAILABLE and wav_path.exists():
        def _play():
            try:
                winsound.PlaySound(str(wav_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()


# Ensure assets upon module import
ensure_sound_assets()

