"""
VICTOR Central State Machine
Manages AI state transitions (IDLE, LISTENING, THINKING, SPEAKING, SLEEPING, OFFLINE)
and coordinates system-wide status updates.
"""

from enum import Enum
import threading
from typing import Callable, List


class SystemState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    SLEEPING = "sleeping"
    OFFLINE = "offline"


class StateManager:
    def __init__(self):
        self._state = SystemState.IDLE
        self._status_message = "VICTOR NEURAL CORE ONLINE"
        self._lock = threading.Lock()
        self._listeners: List[Callable[[SystemState, str], None]] = []

    @property
    def current_state(self) -> SystemState:
        with self._lock:
            return self._state

    @property
    def status_message(self) -> str:
        with self._lock:
            return self._status_message

    def set_state(self, new_state: SystemState, status_message: str = None):
        with self._lock:
            old_state = self._state
            self._state = new_state
            if status_message:
                self._status_message = status_message
            current_status = self._status_message

        # Notify callbacks outside lock to prevent deadlocks
        for listener in self._listeners:
            try:
                listener(new_state, current_status)
            except Exception as e:
                print(f"[!] State listener error: {e}")

    def add_listener(self, callback: Callable[[SystemState, str], None]):
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[SystemState, str], None]):
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)


# Global singleton
state_manager = StateManager()

