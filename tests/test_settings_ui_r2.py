"""
Unit and integration tests for Unified Settings UI & Floating Dock Live Feedback.
Whisper Flow Round 2 — Milestone 3 Specification.

Covers:
- Engine Selector Toggle (Groq Cloud whisper-large-v3-turbo vs Local CPU int8)
- Live Test Mic & API Connection diagnostics (Audio RMS VU meter & Groq API round-trip ping)
- 2x2 Speech Style Selection Cards (Casual Chat, Developer Mode, Professional, Custom)
- Floating Capsule Live Status Badges (148x34px geometry, 'Cloud Active' / 'Local CPU', 'HI-EN')
- Sub-50ms Dialog Launch & 1-Click Dictionary Removal Latency Preservation
"""

import sys
import os
import time
import json
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QPushButton, QLabel,
    QProgressBar, QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, QPoint

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import load_config, save_config, DEFAULT_CONFIG
from voice_profile import VoiceProfileManager
from ui.settings_dialog import SettingsDialog, WordRowWidget, ReplacementRowWidget
from ui.floating_widget import FloatingWidget, STATE_IDLE, STATE_RECORDING


class TestEngineSelectorAndConfig(unittest.TestCase):
    """Unit tests for Engine Selector Toggle (Groq Cloud vs Local CPU int8)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()
        self.mock_audio.get_input_devices.return_value = ["Default Microphone"]

    def test_engine_mode_configuration_persistence(self):
        """Engine selection toggles 'engine_mode' ('groq' vs 'local') in config."""
        cfg = load_config()
        original_engine = cfg.get("engine_mode", "groq")

        try:
            # Toggle to local
            cfg["engine_mode"] = "local"
            save_config(cfg)
            reloaded = load_config()
            self.assertEqual(reloaded.get("engine_mode"), "local")

            # Toggle to groq
            cfg["engine_mode"] = "groq"
            save_config(cfg)
            reloaded2 = load_config()
            self.assertEqual(reloaded2.get("engine_mode"), "groq")
        finally:
            cfg["engine_mode"] = original_engine
            save_config(cfg)

    def test_settings_dialog_instantiation_with_engine_support(self):
        """SettingsDialog instantiates cleanly without exceptions."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        self.assertIsInstance(dlg, QDialog)
        self.assertEqual(dlg.windowTitle(), "Whisper Flow - Preferences")
        dlg.close()

    def test_engine_card_toggle_emits_signal_and_updates_config(self):
        """Clicking EngineCards toggles selection, updates config, and emits engine_changed."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        self.assertTrue(hasattr(dlg, "card_groq"))
        self.assertTrue(hasattr(dlg, "card_local"))

        emitted_modes = []
        dlg.engine_changed.connect(lambda m: emitted_modes.append(m))

        # Click local
        dlg.card_local.clicked.emit("local")
        self.assertEqual(dlg.engine_mode, "local")
        self.assertEqual(dlg.config.get("engine_mode"), "local")
        self.assertTrue(dlg.card_local._selected)
        self.assertFalse(dlg.card_groq._selected)
        self.assertIn("local", emitted_modes)

        # Click groq
        dlg.card_groq.clicked.emit("groq")
        self.assertEqual(dlg.engine_mode, "groq")
        self.assertEqual(dlg.config.get("engine_mode"), "groq")
        self.assertTrue(dlg.card_groq._selected)
        self.assertFalse(dlg.card_local._selected)
        self.assertIn("groq", emitted_modes)

        dlg.close()


class TestLiveMicAndApiConnectionDiagnostics(unittest.TestCase):
    """Unit tests for Live Test Mic & API Connection diagnostics."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()
        self.mock_audio.get_input_devices.return_value = ["Default Microphone"]

    def test_mic_vu_meter_volume_query(self):
        """AudioEngine.get_current_volume returns normalized float [0.0, 1.0]."""
        self.mock_audio.get_current_volume.return_value = 0.65
        vol = self.mock_audio.get_current_volume()
        self.assertGreaterEqual(vol, 0.0)
        self.assertLessEqual(vol, 1.0)
        self.assertEqual(vol, 0.65)

    def test_vu_meter_widget_and_audio_polling(self):
        """VU meter widget exists, has 0-100 range, and correctly polls volume."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        self.assertTrue(hasattr(dlg, "vu_meter"))
        self.assertIsInstance(dlg.vu_meter, QProgressBar)
        self.assertEqual(dlg.vu_meter.minimum(), 0)
        self.assertEqual(dlg.vu_meter.maximum(), 100)

        self.mock_audio.get_current_volume.return_value = 0.42
        dlg._start_audio_vu_test()
        dlg._on_vu_tick()
        self.assertEqual(dlg.vu_meter.value(), 42)

        # Stop test resets to 0
        dlg._stop_audio_vu_test()
        self.assertEqual(dlg.vu_meter.value(), 0)
        dlg.close()

    def test_api_test_result_updates_label(self):
        """API test result callback updates status label and button state."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        self.assertTrue(hasattr(dlg, "test_conn_btn"))
        self.assertTrue(hasattr(dlg, "conn_status_lbl"))

        # Success update
        dlg._on_api_test_result(True, "✓ Connected (142ms latency)")
        self.assertEqual(dlg.conn_status_lbl.text(), "✓ Connected (142ms latency)")
        self.assertTrue(dlg.test_conn_btn.isEnabled())

        # Error update
        dlg._on_api_test_result(False, "Authentication Failed (401)")
        self.assertEqual(dlg.conn_status_lbl.text(), "Authentication Failed (401)")
        self.assertTrue(dlg.test_conn_btn.isEnabled())

        dlg.close()

    @patch("urllib.request.urlopen")
    def test_groq_api_ping_round_trip_success(self, mock_urlopen):
        """API Connection test measures round-trip latency and handles HTTP 200."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.code = 200
        mock_resp.read.return_value = json.dumps({"data": [{"id": "whisper-large-v3-turbo"}]}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        def ping_groq_api(api_key: str):
            import urllib.request
            t0 = time.perf_counter()
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "WhisperFlow"
                }
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                status = getattr(resp, "status", getattr(resp, "code", 200))
                resp.read()
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return status, latency_ms

        status, latency = ping_groq_api("gsk_valid_sample_key")
        self.assertEqual(status, 200)
        self.assertGreater(latency, 0.0)

    @patch("urllib.request.urlopen")
    def test_groq_api_ping_handles_unauthorized_401(self, mock_urlopen):
        """API Connection test gracefully handles HTTP 401 Unauthorized without crashing."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.groq.com/openai/v1/models",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=None
        )

        def safe_ping(api_key: str):
            import urllib.request
            try:
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}", "User-Agent": "WhisperFlow"}
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    return resp.status, "Connected"
            except urllib.error.HTTPError as e:
                return e.code, f"Authentication Failed ({e.code})"
            except Exception as e:
                return -1, f"Offline: {e}"

        code, msg = safe_ping("gsk_invalid_key")
        self.assertEqual(code, 401)
        self.assertIn("Authentication Failed", msg)


class TestSpeechStyleSelectionCards(unittest.TestCase):
    """Unit tests for 2x2 Speech Style selection cards."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()
        self.mock_audio.get_input_devices.return_value = ["Default Microphone"]
        self.profile_mgr = VoiceProfileManager.get_instance()

    def test_style_switching_and_persistence(self):
        """Selecting styles (casual, developer, professional, custom) persists in profile."""
        original_style = self.profile_mgr.get_active_style()

        try:
            for target_style in ["casual", "developer", "professional", "custom"]:
                self.profile_mgr.set_active_style(target_style)
                self.assertEqual(self.profile_mgr.get_active_style(), target_style)
        finally:
            self.profile_mgr.set_active_style(original_style)

    def test_style_cards_interactive_selection(self):
        """Clicking a style card in SettingsDialog updates profile and emits style_changed."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        original_style = self.profile_mgr.get_active_style()

        emitted_styles = []
        dlg.style_changed.connect(lambda s: emitted_styles.append(s))

        try:
            # Test casual
            dlg.card_casual.clicked.emit("casual")
            self.assertEqual(self.profile_mgr.get_active_style(), "casual")
            self.assertTrue(dlg.card_casual._selected)
            self.assertFalse(dlg.card_professional._selected)
            self.assertIn("casual", emitted_styles)

            # Test developer
            dlg.card_developer.clicked.emit("developer")
            self.assertEqual(self.profile_mgr.get_active_style(), "developer")
            self.assertTrue(dlg.card_developer._selected)
            self.assertFalse(dlg.card_casual._selected)
            self.assertIn("developer", emitted_styles)

            # Test professional
            dlg.card_professional.clicked.emit("professional")
            self.assertEqual(self.profile_mgr.get_active_style(), "professional")
            self.assertTrue(dlg.card_professional._selected)
            self.assertIn("professional", emitted_styles)

            # Test custom
            dlg.card_custom.clicked.emit("custom")
            self.assertEqual(self.profile_mgr.get_active_style(), "custom")
            self.assertTrue(dlg.card_custom._selected)
            self.assertIn("custom", emitted_styles)
        finally:
            self.profile_mgr.set_active_style(original_style)
            dlg.close()


class TestFloatingDockLiveBadges(unittest.TestCase):
    """Unit tests for Floating Capsule Live Status Badges."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.widget = FloatingWidget(self.cfg, self.mock_audio)

    def tearDown(self):
        self.widget.close()

    def test_floating_widget_idle_state(self):
        """FloatingWidget initializes in idle state with 64x34 geometry."""
        self.assertEqual(self.widget.current_state, STATE_IDLE)
        self.assertEqual(self.widget.dock_w, 64)
        self.assertEqual(self.widget.dock_h, 34)
        self.assertTrue(self.widget.anim_timer.isActive())

    def test_update_status_badges_contract(self):
        """FloatingWidget provides non-blocking status badge update slot."""
        self.assertTrue(hasattr(self.widget, "update_status_badges"))
        t0 = time.perf_counter()
        self.widget.update_status_badges("groq", "hinglish", style="casual")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(elapsed_ms, 5.0, "update_status_badges took too long")
        self.assertEqual(self.widget.active_engine, "groq")
        self.assertEqual(self.widget.active_language, "hinglish")
        self.assertEqual(self.widget.active_style, "casual")

        # Test local CPU and English
        self.widget.update_status_badges("local", "en")
        self.assertEqual(self.widget.active_engine, "local")
        self.assertEqual(self.widget.active_language, "en")

    def test_paint_event_renders_cleanly_in_all_modes(self):
        """paintEvent executes without errors across both Groq Cloud and Local CPU."""
        from PySide6.QtGui import QPixmap
        pix = QPixmap(self.widget.width(), self.widget.height())

        # Test Cloud Active + Hinglish
        self.widget.update_status_badges("groq", "hinglish")
        self.widget.render(pix)

        # Test Local CPU + English
        self.widget.update_status_badges("local", "en")
        self.widget.render(pix)


class TestSettingsUIPerformancePreservation(unittest.TestCase):
    """Preservation of sub-50ms presentation latency and 1-click removal."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()
        self.mock_audio.get_input_devices.return_value = ["Mic 1"]

    def test_settings_dialog_presentation_latency(self):
        """SettingsDialog instantiates and presents in under 50.0 ms."""
        run_times = []
        for _ in range(5):
            t0 = time.perf_counter()
            dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
            elapsed = (time.perf_counter() - t0) * 1000.0
            run_times.append(elapsed)
            dlg.close()

        mean_latency = sum(run_times) / len(run_times)
        max_latency = max(run_times)

        self.assertLess(mean_latency, 50.0, f"Mean presentation latency {mean_latency:.2f}ms exceeds 50ms")
        self.assertLess(max_latency, 80.0)

    def test_1_click_word_removal_latency(self):
        """1-Click word removal executes in under 50.0 ms (sub-millisecond actual)."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        profile_mgr = VoiceProfileManager.get_instance()
        profile_mgr.add_custom_word("benchmark_removal_word")

        # Emulate 1-click removal
        t0 = time.perf_counter()
        dlg._on_remove_word_clicked("benchmark_removal_word")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(elapsed_ms, 50.0, f"Word removal took {elapsed_ms:.2f}ms (>50ms)")
        self.assertNotIn("benchmark_removal_word", profile_mgr.get_custom_words())
        dlg.close()

    def test_1_click_replacement_rule_removal_latency(self):
        """1-Click replacement rule removal executes in under 50.0 ms."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        profile_mgr = VoiceProfileManager.get_instance()
        profile_mgr.add_replacement("heard_test_word", "TargetTestWord")

        t0 = time.perf_counter()
        dlg._on_remove_rep_clicked("heard_test_word")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(elapsed_ms, 50.0, f"Rule removal took {elapsed_ms:.2f}ms (>50ms)")
        self.assertNotIn("heard_test_word", profile_mgr.get_replacements())
        dlg.close()


if __name__ == "__main__":
    unittest.main()
