"""
VICTOR Live Telemetry & Background Monitor Service
Continuously polls CPU, RAM, GPU (RTX 5060), Disk, Battery, and Service Health (Ollama, STT, WakeWord)
and provides live telemetry snapshots to the UI with power-mode adaptive throttling.
"""

import threading
import time
from typing import Callable, Optional, Dict, Any

from src.actions.computer_control import computer
from src.brain.llm import victor_brain
from src.config.settings import settings


class TelemetryService:
    def __init__(self, interval_sec: Optional[float] = None):
        self._custom_interval = interval_sec
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._callbacks = []
        self._latest_snapshot: Dict[str, Any] = {}
        
        # Ollama check caching to avoid repeated HTTP calls
        self._last_ollama_check: float = 0.0
        self._cached_ollama_ok: bool = False
        self._cached_ollama_msg: str = "Initializing..."

    @property
    def interval(self) -> float:
        """Dynamic interval depending on current power mode."""
        if self._custom_interval is not None:
            return self._custom_interval
        mode = settings.get_power_mode()
        if mode == "performance":
            return settings.get("telemetry.interval_performance", 1.0)
        elif mode == "balanced":
            return settings.get("telemetry.interval_balanced", 2.0)
        else:
            return settings.get("telemetry.interval_low_power", 3.5)

    def add_callback(self, cb: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if cb not in self._callbacks:
                self._callbacks.append(cb)

    def remove_callback(self, cb: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if cb in self._callbacks:
                self._callbacks.remove(cb)

    @property
    def latest_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return self._latest_snapshot.copy()

    def _collect(self) -> Dict[str, Any]:
        data = computer.get_system_telemetry()
        
        # Check Ollama status with 10.0s TTL cache to eliminate HTTP overhead
        now = time.time()
        if now - self._last_ollama_check > 10.0 or self._last_ollama_check == 0.0:
            self._last_ollama_check = now
            self._cached_ollama_ok, self._cached_ollama_msg = victor_brain.check_connection()

        data["ollama_online"] = self._cached_ollama_ok
        data["ollama_message"] = self._cached_ollama_msg
        data["power_mode"] = settings.get_power_mode()
        data["timestamp"] = time.strftime("%H:%M:%S")
        return data

    def _worker(self):
        while self._running:
            try:
                snap = self._collect()
                with self._lock:
                    self._latest_snapshot = snap

                for cb in self._callbacks:
                    try:
                        cb(snap)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[!] Telemetry error: {e}")

            # Sleep for dynamic interval
            time.sleep(self.interval)

    def start(self):
        with self._lock:
            if self._running:
                return
            # Initial snapshot for immediate telemetry availability
            try:
                self._latest_snapshot = self._collect()
            except Exception:
                pass
            self._running = True
            self._thread = threading.Thread(target=self._worker, daemon=True, name="VictorTelemetryThread")
            self._thread.start()

    def stop(self):
        with self._lock:
            self._running = False
            self._thread = None


# Global instance
telemetry_service = TelemetryService()
