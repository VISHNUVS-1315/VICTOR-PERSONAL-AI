"""
Tests for tray mode plumbing: shortcut parsing, settings defaults, autostart helpers.
These run without a GUI or microphone.
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config.settings import settings
from src.core.hotkey import MOD_CONTROL, MOD_NOREPEAT, parse_shortcut


class TestHotkeyParsing(unittest.TestCase):
    def test_default_shortcuts_parse(self):
        for key in ("tray.hotkey_talk", "tray.hotkey_type", "tray.hotkey_stop"):
            shortcut = settings.get(key)
            self.assertTrue(shortcut, f"{key} missing from settings")
            mods, vk = parse_shortcut(shortcut)
            self.assertTrue(mods & MOD_CONTROL, f"{key} should include Ctrl")
            self.assertTrue(mods & MOD_NOREPEAT, "MOD_NOREPEAT should be set")
            self.assertGreater(vk, 0)

    def test_named_keys(self):
        mods, vk = parse_shortcut("ctrl+shift+F9")
        self.assertEqual(vk, 0x78)
        self.assertTrue(mods & MOD_NOREPEAT)

    def test_rejects_incomplete_shortcut(self):
        for bad in ("v", "ctrl+", "ctrl+alt", "ctrl+bogus"):
            with self.assertRaises(ValueError):
                parse_shortcut(bad)


class TestTraySettings(unittest.TestCase):
    def test_tray_defaults_present(self):
        self.assertIsInstance(settings.get("tray.voice_replies"), bool)
        self.assertIsNotNone(settings.get("tray.hotkey_talk"))

    def test_wake_sensitivity_in_range(self):
        value = float(settings.get("voice.wake_word_sensitivity", 0.7))
        self.assertGreaterEqual(value, 0.1)
        self.assertLessEqual(value, 0.95)


class TestAutostartHelpers(unittest.TestCase):
    def test_entry_path_inside_startup_folder(self):
        from scripts.install_autostart import entry_path
        path = entry_path()
        self.assertTrue(str(path).lower().endswith("victor tray.vbs"))
        self.assertIn("start menu", str(path).lower())

    def test_launcher_runs_tray_mode_hidden(self):
        from scripts.install_autostart import _launcher_script
        script = _launcher_script()
        self.assertIn("--tray", script)
        self.assertIn("pythonw.exe", script)
        self.assertIn(", 0, False", script)   # hidden window, do not wait


if __name__ == "__main__":
    unittest.main(verbosity=2)
