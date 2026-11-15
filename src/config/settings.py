"""
VICTOR Configuration & Settings Manager
Handles user preferences, hardware configuration, and application parameters.
"""

import json
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
ASSETS_DIR = ROOT_DIR / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"

CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "assistant_name": "Victor",
    "operator_name": "Vishnu",
    "language_mode": "en",  # en, ta (Tamil), auto
    "power_mode": "low_power",  # low_power, balanced, performance
    "ollama": {
        "host": "http://localhost:11434",
        "chat_endpoint": "/api/chat",
        "tags_endpoint": "/api/tags",
        "model": "qwen3.5:9b",
        "temperature": 0.7,
        "max_context_turns": 15
    },
    "voice": {
        "wake_word": "Victor",
        "wake_word_enabled": True,
        "wake_word_sensitivity": 0.5,
        "mic_index": None,  # None means system default
        "sample_rate": 16000,
        "stt_model": "small",
        "stt_device": "cpu",
        "stt_compute_type": "int8",
        "lazy_load_stt": True,  # Keep memory low in standby
        "speech_threshold": 0.012,
        "silence_duration": 1.0,  # 800-1200ms natural pause endpointing
        "min_speech_duration": 0.5,  # Filter out short clicks/breathing
        "max_record_seconds": 30.0,  # Support complete, long sentences
        "noise_adaptation": True,
        "tts_voice": "david",  # david or zira
        "tts_rate": 170,
        "tts_volume": 1.0,
        "audio_feedback": True
    },
    "ui": {
        "fullscreen": False,
        "power_mode": "low_power",
        "fps_limit": 30,
        "bg_video_enabled": False,
        "bg_video_fps": 18,
        "hud_glow_intensity": 0.8,
        "sound_effects": True
    },
    "telemetry": {
        "interval_low_power": 3.5,
        "interval_balanced": 2.0,
        "interval_performance": 1.0
    },
    "security": {
        "require_confirmation_for_destructive": True,
        "allowed_applications": [
            "code", "cursor", "chrome", "brave", "msedge", "notepad", "calc",
            "cmd", "powershell", "wt", "taskmgr", "explorer", "spotify", "discord"
        ],
        "allowed_scripts_dir": str(ROOT_DIR / "scripts")
    }
}


class Config:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    # Merge with default settings
                    merged = DEFAULT_SETTINGS.copy()
                    for k, v in saved.items():
                        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                            merged[k].update(v)
                        else:
                            merged[k] = v
                    return merged
            except Exception as e:
                print(f"[!] Warning: Failed loading {CONFIG_FILE}: {e}")
        return DEFAULT_SETTINGS.copy()

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4)
        except Exception as e:
            print(f"[!] Failed saving {CONFIG_FILE}: {e}")

    def get(self, key, default=None):
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key, value, auto_save=True):
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        if auto_save:
            self.save()

    @property
    def data(self):
        return self._data

    def get_power_mode(self) -> str:
        return self.get("power_mode", "low_power")

    def set_power_mode(self, mode: str):
        if mode in ("low_power", "balanced", "performance"):
            self.set("power_mode", mode)
            self.set("ui.power_mode", mode)


# Global singleton instance
settings = Config()

