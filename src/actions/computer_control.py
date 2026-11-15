"""
VICTOR Secure Computer Automation System
Executes whitelist-based system actions, application launching, volume/media controls,
screenshots, and hardware diagnostics with strict security constraints and audit logging.
"""

import ctypes
import os
import re
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import psutil
from PIL import ImageGrab

from src.config.settings import ROOT_DIR, DATA_DIR, SCREENSHOTS_DIR, settings
from src.memory.store import log_action

# Try to import pycaw for volume control
try:
    from pycaw.pycaw import AudioUtilities
    PYCAW_AVAILABLE = True
except Exception:
    PYCAW_AVAILABLE = False

# Application Whitelist Mapping (alias -> executable or URI)
APP_WHITELIST = {
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "cursor": "cursor",
    "chrome": "chrome",
    "google chrome": "chrome",
    "brave": "brave",
    "brave browser": "brave",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "powershell": "powershell.exe",
    "command prompt": "cmd.exe",
    "cmd": "cmd.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "files": "explorer.exe",
    "spotify": "spotify",
    "discord": "discord",
    "settings": "ms-settings:",
    "windows settings": "ms-settings:"
}

# Website Shortcuts
WEB_SHORTCUTS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "gmail": "https://mail.google.com",
    "stackoverflow": "https://stackoverflow.com",
    "reddit": "https://www.reddit.com",
    "wikipedia": "https://www.wikipedia.org",
    "arxiv": "https://arxiv.org",
    "maps": "https://maps.google.com",
    "linkedin": "https://www.linkedin.com",
    "ollama": "http://localhost:11434"
}

# Windows Virtual-Key Codes for Media Control
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_KEYUP = 0x0002


class ComputerControl:
    """Secure, permission-based automation system for Windows 11."""

    @staticmethod
    def get_time_and_date() -> str:
        now = datetime.now()
        day_name = now.strftime("%A")
        date_str = now.strftime("%B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        msg = f"It is currently {time_str} on {day_name}, {date_str}."
        log_action("query_time", "system", "success", msg)
        return msg

    @staticmethod
    def open_application(app_name: str) -> Tuple[bool, str]:
        """Launch an application from the approved whitelist."""
        clean_name = app_name.strip().lower()

        # Check whitelist
        target = None
        for alias, cmd in APP_WHITELIST.items():
            if alias in clean_name or clean_name in alias:
                target = cmd
                break

        if not target:
            msg = f"Application '{app_name}' is not in the approved whitelist for security."
            log_action("open_app", app_name, "blocked", msg)
            return False, msg

        try:
            if target.startswith("ms-"):
                os.system(f"start {target}")
            else:
                subprocess.Popen(target, shell=True)

            msg = f"Opened {app_name.title()} successfully."
            log_action("open_app", app_name, "success", msg)
            return True, msg
        except Exception as e:
            err = f"Failed to open {app_name}: {e}"
            log_action("open_app", app_name, "failed", err)
            return False, err

    @staticmethod
    def launch_website(query_or_url: str) -> Tuple[bool, str]:
        """Open a website safely in the default browser."""
        clean = query_or_url.strip().lower()

        # Check known shortcuts
        url = None
        for site_key, site_url in WEB_SHORTCUTS.items():
            if site_key in clean:
                url = site_url
                break

        if not url:
            if clean.startswith("http://") or clean.startswith("https://"):
                url = query_or_url.strip()
            elif "." in clean and " " not in clean:
                url = f"https://{clean}"
            else:
                # Fallback to search query
                from urllib.parse import quote_plus
                url = f"https://www.google.com/search?q={quote_plus(query_or_url)}"

        try:
            webbrowser.open(url)
            msg = f"Launched {url} in browser."
            log_action("launch_website", url, "success", msg)
            return True, msg
        except Exception as e:
            err = f"Failed opening browser: {e}"
            log_action("launch_website", url or query_or_url, "failed", err)
            return False, err

    @staticmethod
    def open_folder(folder_path: str) -> Tuple[bool, str]:
        """Open a user folder safely in File Explorer."""
        clean = folder_path.strip().lower()
        user_home = Path.home()

        target_path: Optional[Path] = None

        # Check standard user directories
        if "download" in clean:
            target_path = user_home / "Downloads"
        elif "document" in clean:
            target_path = user_home / "Documents"
        elif "desktop" in clean:
            target_path = user_home / "Desktop"
        elif "picture" in clean:
            target_path = user_home / "Pictures"
        elif "project" in clean or "victor" in clean:
            target_path = ROOT_DIR
        else:
            p = Path(folder_path)
            if p.exists() and p.is_dir():
                target_path = p

        if not target_path or not target_path.exists():
            msg = f"Folder '{folder_path}' could not be located."
            log_action("open_folder", folder_path, "failed", msg)
            return False, msg

        try:
            os.startfile(str(target_path))
            msg = f"Opened folder: {target_path.name}."
            log_action("open_folder", str(target_path), "success", msg)
            return True, msg
        except Exception as e:
            err = f"Error opening folder: {e}"
            log_action("open_folder", str(target_path), "failed", err)
            return False, err

    @staticmethod
    def take_screenshot() -> Tuple[bool, str]:
        """Capture full screen and save to data/screenshots/."""
        try:
            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"victor_screenshot_{timestamp}.png"
            filepath = SCREENSHOTS_DIR / filename

            img = ImageGrab.grab()
            img.save(str(filepath), "PNG")

            msg = f"Screenshot captured and saved to {filename}."
            log_action("screenshot", str(filepath), "success", msg)
            return True, msg
        except Exception as e:
            err = f"Screenshot capture failed: {e}"
            log_action("screenshot", "screen", "failed", err)
            return False, err

    # Audio Volume Controls
    @staticmethod
    def _get_master_volume_endpoint():
        """Retrieve the default pycaw volume endpoint."""
        if not PYCAW_AVAILABLE:
            return None
        try:
            device = AudioUtilities.GetSpeakers()
            endpoint = device.Activate(
                AudioUtilities.IAudioEndpointVolume._iid_,
                AudioUtilities.CLSCTX_ALL,
                None
            )
            return AudioUtilities.cast(endpoint, AudioUtilities.POINTER(AudioUtilities.IAudioEndpointVolume))
        except Exception:
            return None

    @classmethod
    def get_volume(cls) -> Tuple[int, bool]:
        """Get current system volume level (0-100) and mute state."""
        endpoint = cls._get_master_volume_endpoint()
        if endpoint:
            try:
                scalar = endpoint.GetMasterVolumeLevelScalar()
                muted = endpoint.GetMute()
                return int(scalar * 100), bool(muted)
            except Exception:
                pass
        return 50, False

    @classmethod
    def set_volume(cls, percent: int) -> Tuple[bool, str]:
        """Set volume level between 0 and 100%."""
        percent = max(0, min(100, int(percent)))
        endpoint = cls._get_master_volume_endpoint()
        if endpoint:
            try:
                endpoint.SetMasterVolumeLevelScalar(percent / 100.0, None)
                if percent > 0 and endpoint.GetMute():
                    endpoint.SetMute(0, None)
                msg = f"System volume set to {percent}%."
                log_action("volume_set", f"{percent}%", "success", msg)
                return True, msg
            except Exception as e:
                err = f"Failed setting volume: {e}"
                log_action("volume_set", f"{percent}%", "failed", err)
                return False, err
        return False, "Audio endpoint control not available."

    @classmethod
    def change_volume(cls, delta: int) -> Tuple[bool, str]:
        """Increase or decrease volume by delta percent."""
        curr, _ = cls.get_volume()
        new_level = max(0, min(100, curr + delta))
        return cls.set_volume(new_level)

    @classmethod
    def set_mute(cls, mute: bool) -> Tuple[bool, str]:
        """Mute or unmute master volume."""
        endpoint = cls._get_master_volume_endpoint()
        if endpoint:
            try:
                endpoint.SetMute(1 if mute else 0, None)
                state_str = "muted" if mute else "unmuted"
                msg = f"System volume {state_str}."
                log_action("volume_mute", state_str, "success", msg)
                return True, msg
            except Exception as e:
                return False, f"Failed muting: {e}"
        return False, "Audio control not available."

    # Media Playback Controls
    @staticmethod
    def media_control(action: str) -> Tuple[bool, str]:
        """Send virtual media keystrokes (play/pause, next, prev, stop)."""
        action = action.lower().strip()
        vk_code = None

        if "play" in action or "pause" in action or "toggle" in action:
            vk_code = VK_MEDIA_PLAY_PAUSE
            name = "Play/Pause"
        elif "next" in action or "skip" in action:
            vk_code = VK_MEDIA_NEXT_TRACK
            name = "Next Track"
        elif "previous" in action or "prev" in action or "back" in action:
            vk_code = VK_MEDIA_PREV_TRACK
            name = "Previous Track"
        elif "stop" in action:
            vk_code = VK_MEDIA_STOP
            name = "Stop Playback"

        if not vk_code:
            return False, f"Unknown media command: '{action}'"

        try:
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
            msg = f"Triggered media {name}."
            log_action("media_control", name, "success", msg)
            return True, msg
        except Exception as e:
            return False, f"Media control error: {e}"

    # Search Local Files
    @staticmethod
    def search_local_files(query: str, limit: int = 8) -> List[str]:
        """Safely search user home and project directories for files matching query."""
        results = []
        clean_q = query.strip().lower()
        if not clean_q or len(clean_q) < 3:
            return ["Please specify a longer search term (at least 3 characters)."]

        search_roots = [
            Path.home() / "Desktop",
            Path.home() / "Documents",
            Path.home() / "Downloads",
            ROOT_DIR
        ]

        count = 0
        for root in search_roots:
            if not root.exists():
                continue
            try:
                for p in root.rglob(f"*{clean_q}*"):
                    if any(ignored in p.parts for ignored in [".git", ".venv", "__pycache__", "node_modules", "AppData"]):
                        continue
                    if p.is_file():
                        results.append(f"{p.name} ({p.parent})")
                        count += 1
                        if count >= limit:
                            break
            except Exception:
                continue
            if count >= limit:
                break

        if not results:
            return [f"No files matching '{query}' were found in standard directories."]
        return results

    # Hardware & System Telemetry
    _last_gpu_check: float = 0.0
    _cached_gpu_info: Dict[str, Any] = {
        "name": "NVIDIA RTX 5060 Laptop",
        "utilization": 0,
        "temperature": 0,
        "vram_used_mb": 0,
        "vram_total_mb": 8151,
        "available": False
    }

    @classmethod
    def get_system_telemetry(cls) -> Dict[str, Any]:
        """Retrieve real-time hardware status: CPU, RAM, Disk, GPU, Battery with caching for low overhead."""
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")

        # Battery
        battery = psutil.sensors_battery()
        battery_pct = battery.percent if battery else 100
        power_plugged = battery.power_plugged if battery else True

        # NVIDIA GPU Diagnostics - Cached with 4.0s TTL to prevent waking GPU & CPU spikes
        now = time.time()
        if now - cls._last_gpu_check > 4.0:
            cls._last_gpu_check = now
            try:
                # Use CREATE_NO_WINDOW flag on Windows to minimize process creation overhead
                startupinfo = None
                creationflags = 0
                if os.name == "nt":
                    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

                res = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=1.2,
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                if res.returncode == 0 and res.stdout.strip():
                    parts = [p.strip() for p in res.stdout.strip().split(",")]
                    if len(parts) >= 4:
                        cls._cached_gpu_info["utilization"] = int(parts[0])
                        cls._cached_gpu_info["temperature"] = int(parts[1])
                        cls._cached_gpu_info["vram_used_mb"] = int(parts[2])
                        cls._cached_gpu_info["vram_total_mb"] = int(parts[3])
                        cls._cached_gpu_info["available"] = True
            except Exception:
                pass

        gpu_info = cls._cached_gpu_info.copy()

        return {
            "cpu_percent": cpu_pct,
            "cpu_cores": psutil.cpu_count(logical=True),
            "ram_percent": mem.percent,
            "ram_used_gb": round(mem.used / (1024 ** 3), 1),
            "ram_total_gb": round(mem.total / (1024 ** 3), 1),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024 ** 3), 1),
            "battery_percent": battery_pct,
            "power_plugged": power_plugged,
            "gpu": gpu_info
        }

    @classmethod
    def get_system_report(cls) -> str:
        """Generate a concise, human-readable system diagnostic report."""
        stats = cls.get_system_telemetry()
        gpu = stats["gpu"]

        report = (
            f"System Telemetry: CPU usage is at {stats['cpu_percent']}%. "
            f"RAM is at {stats['ram_percent']}% ({stats['ram_used_gb']} GB used of {stats['ram_total_gb']} GB). "
            f"Disk C: has {stats['disk_free_gb']} GB available. "
        )

        if gpu["available"]:
            report += f"RTX 5060 GPU is operating at {gpu['temperature']}°C with {gpu['utilization']}% utilization and {gpu['vram_used_mb']} MB VRAM active. "

        if not stats["power_plugged"]:
            report += f"Battery is at {stats['battery_percent']}%. "

        log_action("system_telemetry", "hardware", "success", report)
        return report


# Global instance
computer = ComputerControl()

