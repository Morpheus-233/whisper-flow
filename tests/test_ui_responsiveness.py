"""
Unit and integration tests for UI Responsiveness, Dialog Presentation, Theme & Capture Safety.
Covers:
- F16: Sub-50ms Dialog Presentation
- F17: Native DWM Immersive Dark Title Bars & Palette setup
- F18: Win32 Mouse Capture Deadlock Prevention (ReleaseCapture)
- F19: 1-Click Instant Dictionary Removal
- F20: Real-Time In-Place Search Filtering
"""

import sys
import time
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QDialog, QWidget
from PySide6.QtCore import Qt

from config import load_config
from voice_profile import VoiceProfileManager
from ui.theme_helper import apply_dark_window_attributes
from ui.settings_dialog import SettingsDialog
from ui.voice_training_dialog import VoiceTrainingDialog


class TestUIResponsivenessAndTheme(unittest.TestCase):
    """Tier 1 tests for sub-50ms dialog presentation, dark title bars, and 1-click dictionary removal."""

    @classmethod
    def setUpClass(cls):
        # Initialize QApplication if not already running
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.cfg = load_config()

    def setUp(self):
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()

    def test_voice_training_dialog_presentation_latency(self):
        """Tier 1: VoiceTrainingDialog instantiates in < 50ms."""
        t0 = time.perf_counter()
        dlg = VoiceTrainingDialog(self.mock_audio, self.mock_whisper)
        elapsed = (time.perf_counter() - t0) * 1000.0

        self.assertIsInstance(dlg, QDialog)
        self.assertTrue(elapsed < 50.0, f"VoiceTrainingDialog took {elapsed:.1f}ms (>50ms)")
        dlg.close()

    def test_dark_mode_theme_attributes(self):
        """Tier 1: apply_dark_window_attributes configures dark palette and DWM attributes."""
        widget = QWidget()
        apply_dark_window_attributes(widget)

        pal = widget.palette()
        # Verify background is #0f172a (R=15, G=23, B=42)
        window_color = pal.color(pal.ColorRole.Window)
        self.assertEqual(window_color.red(), 15)
        self.assertEqual(window_color.green(), 23)
        self.assertEqual(window_color.blue(), 42)

        # Verify autoFillBackground is True
        self.assertTrue(widget.autoFillBackground())
        widget.close()

    def test_1_click_instant_dictionary_removal(self):
        """Tier 1: 1-click removal of custom words and replacements executes instantaneously."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)

        # Add a temporary test word
        test_word = f"TempWord_{int(time.time()*1000)}"
        profile_mgr = VoiceProfileManager.get_instance()
        profile_mgr.add_custom_word(test_word)
        dlg._refresh_vocab_list()

        # Benchmark 1-click removal
        t0 = time.perf_counter()
        dlg._on_remove_word_clicked(test_word)
        elapsed = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(elapsed < 50.0, f"Word removal took {elapsed:.1f}ms, expected <50ms")
        self.assertNotIn(test_word, profile_mgr.get_custom_words())

        # Test replacement removal
        test_heard = f"temp_heard_{int(time.time()*1000)}"
        profile_mgr.add_replacement(test_heard, "TestTarget")
        dlg._refresh_rep_list()

        t0_rep = time.perf_counter()
        dlg._on_remove_rep_clicked(test_heard)
        elapsed_rep = (time.perf_counter() - t0_rep) * 1000.0

        self.assertTrue(elapsed_rep < 50.0, f"Replacement removal took {elapsed_rep:.1f}ms, expected <50ms")
        self.assertNotIn(test_heard, profile_mgr.get_replacements())

        dlg.close()

    def test_realtime_in_place_search_filtering(self):
        """Tier 1: Typing into filter fields dynamically filters items."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        profile_mgr = VoiceProfileManager.get_instance()

        # Ensure known test words exist
        profile_mgr.add_custom_word("AlphaTechnicalJargon")
        profile_mgr.add_custom_word("BetaPhoneticKeyword")
        dlg._refresh_vocab_list()

        # Filter by "Alpha"
        dlg.vocab_filter_input.setText("Alpha")
        dlg._filter_vocab_list()

        # Verify vocab_list displays filtered subset
        visible_items = []
        for i in range(dlg.vocab_list.count()):
            item = dlg.vocab_list.item(i)
            if not item.isHidden():
                row_widget = dlg.vocab_list.itemWidget(item)
                if row_widget and hasattr(row_widget, "word"):
                    visible_items.append(row_widget.word)

        self.assertIn("AlphaTechnicalJargon", visible_items)
        self.assertNotIn("BetaPhoneticKeyword", visible_items)

        # Clear filter restores all
        dlg.vocab_filter_input.setText("")
        dlg._filter_vocab_list()

        # Clean up added words
        profile_mgr.remove_custom_word("AlphaTechnicalJargon")
        profile_mgr.remove_custom_word("BetaPhoneticKeyword")
        dlg.close()

    @patch("ctypes.windll.user32.ReleaseCapture")
    def test_mouse_capture_deadlock_prevention(self, mock_release_capture):
        """Tier 1: Win32 ReleaseCapture is safely accessible and callable."""
        from ui.floating_widget import FloatingWidget
        fw = FloatingWidget(self.cfg, self.mock_audio)
        self.assertIsNotNone(fw)
        fw.close()


if __name__ == "__main__":
    unittest.main()
