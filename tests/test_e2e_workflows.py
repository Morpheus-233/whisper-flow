"""
Integration and End-to-End Workflow Tests.
Covers:
- Tier 3: Cross-Feature Combinations:
  - Phonetic dictionary replacement + Casual styling pipeline
  - Developer mode syntax + Voice profile replacements
  - App-aware style resolution based on window context
- Tier 4: Real-world Workload Scenarios:
  - Calibration session leading to active transcription replacement
  - Simulated zero-GPU bilingual dictation pipeline
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

import calibration_engine
from voice_profile import VoiceProfileManager
from text_cleaner import format_casual_chat
from style_engine import StyleEngine

try:
    from style_engine import format_developer_mode
except ImportError:
    try:
        from text_cleaner import format_developer_mode
    except ImportError:
        format_developer_mode = getattr(StyleEngine, "format_developer_mode", None)


class TestCrossFeatureCombinations(unittest.TestCase):
    """Tier 3 tests: verifying interaction and composition of multiple subsystems."""

    def test_phonetic_replacement_combined_with_casual_styling(self):
        """
        Tests the composition:
        Raw spoken text -> VoiceProfileManager.apply_replacements -> format_casual_chat.
        Verifies that punctuation-laden keys (e.g. 'cooper nets,') are replaced before
        casual formatting strips trailing periods/casing.
        """
        mgr = VoiceProfileManager.get_instance()
        original_reps = dict(mgr.get_replacements())

        try:
            mgr.profile["word_replacements"] = {
                "cooper nets,": "Kubernetes",
                "pie side": "PySide6"
            }

            raw_input = "We deploy on cooper nets, with pie side apps."

            # Step 1: Apply voice profile replacements
            replaced = mgr.apply_replacements(raw_input)
            self.assertEqual(replaced, "We deploy on Kubernetes with PySide6 apps.")

            # Step 2: Apply casual chat styling
            casual_output = format_casual_chat(replaced)
            self.assertEqual(casual_output, "we deploy on kubernetes with PySide6 apps")
            self.assertFalse(casual_output.endswith("."))
        finally:
            mgr.profile["word_replacements"] = original_reps

    def test_app_aware_style_resolution(self):
        """
        Tests that VoiceProfileManager accurately selects active style based on
        active foreground window titles and window classes.
        """
        mgr = VoiceProfileManager.get_instance()
        original_app_aware = mgr.profile.get("app_aware_enabled", True)
        original_style = mgr.profile.get("active_style", "raw")

        try:
            mgr.profile["app_aware_enabled"] = True
            mgr.profile["active_style"] = "raw"

            # 1. Developer context: Terminal / VS Code
            style_ide = mgr.get_effective_style(window_title="whisper-flow — Visual Studio Code", window_class="Chrome_WidgetWin_1")
            self.assertEqual(style_ide, "code")

            # 2. Casual context: Discord / Slack
            style_chat = mgr.get_effective_style(window_title="general | Discord", window_class="Chrome_WidgetWin_1")
            self.assertEqual(style_chat, "casual")

            # 3. Professional context: Microsoft Word / Outlook
            style_doc = mgr.get_effective_style(window_title="Document1 - Microsoft Word", window_class="OpusApp")
            self.assertEqual(style_doc, "professional")

            # 4. Unknown context defaults to active_style
            style_other = mgr.get_effective_style(window_title="Calculator", window_class="ApplicationFrameWindow")
            self.assertEqual(style_other, "raw")
        finally:
            mgr.profile["app_aware_enabled"] = original_app_aware
            mgr.profile["active_style"] = original_style

    def test_developer_mode_and_phonetic_replacement_composition(self):
        """
        Tests composition of voice profile replacement with developer syntax.
        """
        if format_developer_mode is None:
            self.skipTest("format_developer_mode pending in M2")

        mgr = VoiceProfileManager.get_instance()
        original_reps = dict(mgr.get_replacements())

        try:
            mgr.profile["word_replacements"] = {"pie side": "PySide6"}
            raw_text = "const widget equals open paren pie side close paren"

            # Voice replacement
            replaced = mgr.apply_replacements(raw_text)
            self.assertIn("PySide6", replaced)

            # Developer mode
            dev_output = format_developer_mode(replaced)
            self.assertIn("(PySide6)", dev_output)
        finally:
            mgr.profile["word_replacements"] = original_reps


class TestRealWorldWorkloadScenarios(unittest.TestCase):
    """Tier 4 tests: End-to-end multi-step workflow simulations."""

    def test_calibration_session_leading_to_active_transcription_replacement(self):
        """
        Simulates the full user calibration workflow:
        1. Load dataset sentence #51 (Hindi/Hinglish).
        2. User speaks with slight regional accent/mispronunciation.
        3. compute_diff extracts misheard pairs with stripped punctuation.
        4. auto_register_misheard_pairs registers them into voice profile.
        5. Live dictation automatically uses newly registered corrections.
        """
        mgr = VoiceProfileManager.get_instance()
        original_reps = dict(mgr.get_replacements())

        try:
            # Clean test keys from replacements to test registration
            mgr.profile["word_replacements"] = {k: v for k, v in original_reps.items() if k not in ("me", "hu")}

            # 1. Load dataset
            dataset = calibration_engine.load_calibration_dataset()
            sentence_51 = next(s for s in dataset if s["id"] == 51)
            target_text = sentence_51["text"]
            self.assertEqual(target_text, "Main thodi der mein call karta hoon.")

            # 2. User says 'me' instead of 'mein' and 'hu' instead of 'hoon.'
            user_spoken = "main thodi der me call karta hu"

            # 3. Compute accuracy diff
            diff_result = calibration_engine.compute_diff(
                target_text,
                user_spoken,
                phonetic_keywords=sentence_51["phonetic_keywords"]
            )
            self.assertTrue(diff_result["accuracy"] > 50.0)
            misheard = diff_result["misheard_pairs"]
            self.assertTrue(len(misheard) >= 1)

            # 4. Auto-register corrections into voice profile
            registered_count = calibration_engine.auto_register_misheard_pairs(misheard, mgr)
            self.assertTrue(registered_count >= 1)

            # 5. Subsequent live dictation: user speaks sentence containing 'hu' and 'me'
            subsequent_dictation = "main hu ek developer aur me yahan kaam karta hu"
            corrected = mgr.apply_replacements(subsequent_dictation)

            # Both 'hu' -> 'hoon' and 'me' -> 'mein' should be replaced
            self.assertIn("hoon", corrected)
            self.assertIn("mein", corrected)
            self.assertNotIn("hu", corrected.split())
            self.assertNotIn("me", corrected.split())

            # 6. Apply casual styling
            final_chat = format_casual_chat(corrected)
            self.assertIn("hoon", final_chat)
            self.assertIn("mein", final_chat)
            self.assertFalse(final_chat.endswith("."))
        finally:
            mgr.profile["word_replacements"] = original_reps

    def test_simulated_zero_gpu_dictation_pipeline(self):
        """
        Simulates end-to-end transcription pipeline:
        Audio Array -> WhisperEngine -> VoiceProfile Replacements -> Text Cleaner.
        """
        mgr = VoiceProfileManager.get_instance()
        original_words = list(mgr.get_custom_words())
        original_reps = dict(mgr.get_replacements())

        try:
            mgr.profile["custom_words"] = ["WhisperFlow", "CTranslate2", "Hinglish"]
            mgr.profile["word_replacements"] = {}

            # 1. Generate biasing prompt
            prompt = mgr.get_initial_prompt()
            self.assertIn("WhisperFlow", prompt)

            # 2. Mock WhisperEngine transcription using greedy decoding
            from whisper_engine import WhisperEngine
            engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8")
            engine.engine_mode = "local"

            mock_model = MagicMock()
            mock_seg = MagicMock()
            mock_seg.text = "whisper flow performs zero GPU inference with see translate."
            mock_model.transcribe.return_value = ([mock_seg], MagicMock())
            engine.model = mock_model

            synthetic_audio = np.ones(16000, dtype=np.float32) * 0.05
            raw_text = engine.transcribe(synthetic_audio, initial_prompt=prompt)
            self.assertEqual(raw_text, "whisper flow performs zero GPU inference with see translate.")

            # 3. Phonetic replacement
            mgr.profile["word_replacements"] = {
                "whisper flow": "Whisper Flow",
                "see translate": "CTranslate2"
            }
            replaced = mgr.apply_replacements(raw_text)
            self.assertEqual(replaced, "Whisper Flow performs zero GPU inference with CTranslate2.")

            # 4. Casual styling
            final_text = format_casual_chat(replaced)
            self.assertEqual(final_text, "whisper flow performs zero GPU inference with CTranslate2")
        finally:
            mgr.profile["custom_words"] = original_words
            mgr.profile["word_replacements"] = original_reps


if __name__ == "__main__":
    unittest.main()
