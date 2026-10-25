import sys
import os
import time
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = r"C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap
from config import load_config, save_config, DEFAULT_CONFIG
from voice_profile import VoiceProfileManager
from ui.settings_dialog import SettingsDialog, EngineCard, StyleCard
from ui.floating_widget import FloatingWidget, STATE_IDLE, STATE_RECORDING
from audio_engine import AudioEngine

class AdversarialM3Audit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()

    def test_engine_card_edge_cases(self):
        """Test EngineCard with empty strings, rapid clicks, selection states."""
        card = EngineCard("test_mode", "Test Title", "Test Subtitle", "BADGE")
        self.assertFalse(card._selected)
        
        # Test selection toggle
        card.set_selected(True)
        self.assertTrue(card._selected)
        card.set_selected(False)
        self.assertFalse(card._selected)

        # Test card without badge
        card_no_badge = EngineCard("mode2", "Title2", "Sub2", "")
        self.assertIsNone(card_no_badge.badge_lbl)
        card_no_badge.set_selected(True)
        self.assertTrue(card_no_badge._selected)

    def test_style_card_edge_cases(self):
        """Test StyleCard with various keys and selection toggling."""
        card = StyleCard("casual", "Casual", "Subtitle", "0ms")
        self.assertFalse(card._selected)
        self.assertEqual(card.check_lbl.text(), "")

        card.set_selected(True)
        self.assertTrue(card._selected)
        self.assertEqual(card.check_lbl.text(), "✓")

        card.set_selected(False)
        self.assertFalse(card._selected)
        self.assertEqual(card.check_lbl.text(), "")

    def test_settings_dialog_with_none_engines(self):
        """Test SettingsDialog when audio_engine and whisper_engine are None."""
        dlg = SettingsDialog(self.cfg, audio_engine=None, whisper_engine=None)
        
        # Audio test should handle None audio_engine gracefully
        dlg._start_audio_vu_test()
        dlg._on_vu_tick()
        self.assertEqual(dlg.vu_meter.value(), 0)
        dlg._stop_audio_vu_test()

        # Engine card clicking should update config even without whisper_engine
        dlg._on_engine_card_clicked("local")
        self.assertEqual(dlg.engine_mode, "local")
        self.assertEqual(dlg.config.get("engine_mode"), "local")

        dlg._on_engine_card_clicked("groq")
        self.assertEqual(dlg.engine_mode, "groq")
        self.assertEqual(dlg.config.get("engine_mode"), "groq")

        # Style card selection
        for style in ["casual", "developer", "professional", "custom", "unknown_custom"]:
            dlg._select_style(style, emit_signal=False)

        dlg.close()

    def test_settings_dialog_rapid_vu_meter_cycles(self):
        """Test rapid starting and stopping of audio VU meter test."""
        mock_audio = MagicMock()
        mock_audio.is_recording = False
        mock_audio.get_current_volume.return_value = 0.85
        
        dlg = SettingsDialog(self.cfg, audio_engine=mock_audio, whisper_engine=None)
        for _ in range(10):
            dlg._start_audio_vu_test()
            dlg._on_vu_tick()
            self.assertEqual(dlg.vu_meter.value(), 85)
            dlg._stop_audio_vu_test()
            self.assertEqual(dlg.vu_meter.value(), 0)
        dlg.close()

    def test_settings_dialog_api_ping_error_handling(self):
        """Verify API ping handles network exceptions gracefully without crashing."""
        dlg = SettingsDialog(self.cfg, audio_engine=None, whisper_engine=None)
        
        # 1. Empty key
        dlg.groq_key_input.setText("")
        dlg._start_groq_ping_test()
        self.assertIn("Invalid Key", dlg.conn_status_lbl.text())

        # 2. Mock HTTP 401
        with patch("urllib.request.urlopen") as mock_url:
            import urllib.error
            mock_url.side_effect = urllib.error.HTTPError("https://api.groq.com", 401, "Unauthorized", {}, None)
            dlg.groq_key_input.setText("gsk_bad_key")
            dlg._start_groq_ping_test()
            time.sleep(0.05)
            self.app.processEvents()
            self.assertIn("Authentication Failed (401)", dlg.conn_status_lbl.text())

        # 3. Mock HTTP 429
        with patch("urllib.request.urlopen") as mock_url:
            import urllib.error
            mock_url.side_effect = urllib.error.HTTPError("https://api.groq.com", 429, "Rate Limit", {}, None)
            dlg.groq_key_input.setText("gsk_bad_key")
            dlg._start_groq_ping_test()
            time.sleep(0.05)
            self.app.processEvents()
            self.assertIn("Rate Limit Exceeded (429)", dlg.conn_status_lbl.text())

        # 4. Mock URLError (offline)
        with patch("urllib.request.urlopen") as mock_url:
            import urllib.error
            mock_url.side_effect = urllib.error.URLError("Connection refused")
            dlg.groq_key_input.setText("gsk_bad_key")
            dlg._start_groq_ping_test()
            time.sleep(0.05)
            self.app.processEvents()
            self.assertIn("Offline", dlg.conn_status_lbl.text())

        dlg.close()

    def test_floating_widget_rendering_stress(self):
        """Stress-test FloatingWidget render across multiple engine, lang, and style states."""
        mock_audio = MagicMock()
        widget = FloatingWidget(self.cfg, mock_audio)
        pix = QPixmap(widget.width(), widget.height())

        test_matrices = [
            ("groq", "hinglish", "casual"),
            ("groq", "en", "developer"),
            ("local", "hinglish", "professional"),
            ("local", "en", "custom"),
            ("unknown_engine", "unknown_lang", None),
        ]

        for engine, lang, style in test_matrices:
            widget.update_status_badges(engine, lang, style)
            widget.render(pix)
            self.assertEqual(widget.active_engine, engine)
            self.assertEqual(widget.active_language, lang)

        widget.close()

if __name__ == "__main__":
    unittest.main()
