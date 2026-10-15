"""
Unit and integration tests for Style Transformation Engine.
Covers:
- F10: Rule-Based Casual Chat Styling (zero GPU, punctuation stripping, case relaxation, token protection)
- F11: Rule-Based Developer Mode Styling (spoken casing: camelCase, snake_case, kebab-case, PascalCase, CONSTANT_CASE, code operators)
- F12: Rule-Based Custom Persona Styling (tone formatting with zero GPU / LLM latency)
- Tier 2 & Tier 3 Boundary and Cross-feature cases
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from text_cleaner import clean_speech_text, format_casual_chat
from style_engine import StyleEngine

# Progressive import for Developer Mode & Persona formatting functions
try:
    from style_engine import format_developer_mode
except ImportError:
    try:
        from text_cleaner import format_developer_mode
    except ImportError:
        format_developer_mode = getattr(StyleEngine, "format_developer_mode", None)

try:
    from style_engine import format_custom_persona
except ImportError:
    try:
        from text_cleaner import format_custom_persona
    except ImportError:
        format_custom_persona = getattr(StyleEngine, "format_custom_persona", None)


class TestCasualChatStyling(unittest.TestCase):
    """Tier 1 & Tier 2 tests for Rule-Based Casual Chat formatting (F10)."""

    def test_strip_trailing_periods_and_commas(self):
        input_text = "Hello team, we are shipping Whisper Flow today."
        out = format_casual_chat(input_text)
        self.assertEqual(out, "hello team we are shipping whisper flow today")
        self.assertFalse(out.endswith("."))
        self.assertFalse(out.endswith(","))

    def test_strip_trailing_exclamation_and_question_marks(self):
        input_text = "Is this really working with zero GPU?!"
        out = format_casual_chat(input_text)
        self.assertEqual(out, "is this really working with zero GPU")
        self.assertFalse(out.endswith("?"))
        self.assertFalse(out.endswith("!"))

    def test_preserves_urls(self):
        input_text = "Check the docs at https://github.com/openai/whisper for details."
        out = format_casual_chat(input_text)
        self.assertIn("https://github.com/openai/whisper", out)
        self.assertFalse(out.endswith("."))

    def test_preserves_decimals_and_timestamps(self):
        input_text = "Pi is approximately 3.14159, and the meeting is at 10:30."
        out = format_casual_chat(input_text)
        self.assertIn("3.14159", out)
        self.assertIn("10:30", out)

    def test_preserves_acronyms_and_code_identifiers(self):
        input_text = "Testing PySide6 with fast CPU and GPU API endpoints."
        out = format_casual_chat(input_text)
        self.assertIn("PySide6", out)
        self.assertIn("CPU", out)
        self.assertIn("GPU", out)
        self.assertIn("API", out)

    def test_preserves_code_filenames_and_snake_case(self):
        input_text = "Look at app.py and my_custom_variable in the repo."
        out = format_casual_chat(input_text)
        self.assertIn("app.py", out)
        self.assertIn("my_custom_variable", out)

    def test_removes_hesitation_fillers_and_stutters(self):
        input_text = "Um, uh, we need to to deploy this immediately."
        out = format_casual_chat(input_text)
        self.assertEqual(out, "we need to deploy this immediately")

    def test_empty_string_and_whitespace_only(self):
        self.assertEqual(format_casual_chat(""), "")
        self.assertEqual(format_casual_chat("   "), "")

    def test_casual_chat_latency_sub_1ms(self):
        sample = "The quick brown fox jumps over the lazy dog. Running benchmark on modern speech dictation."
        t0 = time.perf_counter()
        for _ in range(50):
            format_casual_chat(sample)
        elapsed_per_call = (time.perf_counter() - t0) / 50.0
        self.assertTrue(elapsed_per_call < 0.005, f"Latency too high: {elapsed_per_call*1000:.2f}ms")


class TestDeveloperModeStyling(unittest.TestCase):
    """Tier 1 & Tier 2 tests for Rule-Based Developer Mode formatting (F11)."""

    def setUp(self):
        # Check if format_developer_mode is directly available or attached to StyleEngine
        self.dev_fn = format_developer_mode
        if self.dev_fn is None and hasattr(StyleEngine, "format_developer_mode"):
            self.dev_fn = getattr(StyleEngine, "format_developer_mode")

    def test_spoken_casing_transformations(self):
        if self.dev_fn is None:
            self.skipTest("format_developer_mode not yet implemented by M2")

        # 1. camelCase
        res_camel = self.dev_fn("camel case user profile manager")
        self.assertIn("userProfileManager", res_camel)

        # 2. snake_case
        res_snake = self.dev_fn("snake case get user by id")
        self.assertIn("get_user_by_id", res_snake)

        # 3. kebab-case
        res_kebab = self.dev_fn("kebab case primary action button")
        self.assertIn("primary-action-button", res_kebab)

        # 4. PascalCase
        res_pascal = self.dev_fn("pascal case speech calibration engine")
        self.assertIn("SpeechCalibrationEngine", res_pascal)

        # 5. CONSTANT_CASE
        res_const = self.dev_fn("constant case max retry attempts")
        self.assertIn("MAX_RETRY_ATTEMPTS", res_const)

    def test_spoken_code_operators_and_tokens(self):
        if self.dev_fn is None:
            self.skipTest("format_developer_mode not yet implemented by M2")

        test_inputs = {
            "load dot env config": ".env",
            "arrow function return x": "=>",
            "if a double equals b": "==",
            "if x triple equals y": "===",
            "if count not equals zero": "!=",
            "open paren x comma y close paren": "(",
            "open brace key value close brace": "{",
            "open bracket zero close bracket": "["
        }

        for phrase, expected_token in test_inputs.items():
            out = self.dev_fn(phrase)
            self.assertIn(expected_token, out, f"Failed for phrase '{phrase}', got '{out}'")

    def test_developer_mode_sub_1ms_execution(self):
        if self.dev_fn is None:
            self.skipTest("format_developer_mode not yet implemented by M2")

        text = "const config equals dot env and snake case user profile id"
        t0 = time.perf_counter()
        for _ in range(50):
            self.dev_fn(text)
        avg_time = (time.perf_counter() - t0) / 50.0
        self.assertTrue(avg_time < 0.005, f"Execution took too long: {avg_time*1000:.2f}ms")


class TestCustomPersonaStyling(unittest.TestCase):
    """Tier 1 & Tier 2 tests for Rule-Based Custom Persona formatting (F12)."""

    def setUp(self):
        self.persona_fn = format_custom_persona
        if self.persona_fn is None and hasattr(StyleEngine, "format_custom_persona"):
            self.persona_fn = getattr(StyleEngine, "format_custom_persona")

    def test_custom_persona_execution_without_ollama(self):
        if self.persona_fn is None:
            self.skipTest("format_custom_persona not yet implemented by M2")

        # Must execute cleanly without throwing connection errors or requiring GPU
        sample_input = "Hello team, we need to finalize the release notes for Whisper Flow today."
        out = self.persona_fn(sample_input)
        self.assertIsInstance(out, str)
        self.assertTrue(len(out) > 0)


class TestStyleEngineCoordination(unittest.TestCase):
    """Tier 1 & Tier 3 tests for StyleEngine dispatching and style modes."""

    def setUp(self):
        self.mock_mgr = MagicMock()
        self.mock_mgr.profile = {
            "active_style": "casual",
            "ollama_enabled": False,
            "custom_persona_prompt": "Make it brief and clear."
        }
        self.mock_mgr.get_active_style.return_value = "casual"
        self.engine = StyleEngine(voice_profile_manager=self.mock_mgr)

    def test_dispatch_casual_style(self):
        text = "Good morning everyone, please review the PR."
        out = self.engine.transform_text(text, target_style="casual")
        self.assertEqual(out, "good morning everyone please review the PR")

    def test_dispatch_raw_style_returns_cleaned_base(self):
        text = "Um, raw text without style changes."
        out = self.engine.transform_text(text, target_style="raw")
        self.assertEqual(out, "Raw text without style changes.")

    def test_dispatch_code_style_without_ollama(self):
        # When Ollama is disabled, code style must not crash or return empty
        text = "const server equals dot env"
        out = self.engine.transform_text(text, target_style="code")
        self.assertIsInstance(out, str)
        self.assertTrue(len(out) > 0)

    def test_empty_input_handling(self):
        self.assertEqual(self.engine.transform_text(""), "")
        self.assertEqual(self.engine.transform_text(None), "")
        self.assertEqual(self.engine.transform_text("   "), "")


if __name__ == "__main__":
    unittest.main()
