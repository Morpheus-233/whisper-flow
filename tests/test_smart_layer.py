"""
Unit tests for the Smart Filtering & Formatting Layer:
- Speech retractions & self-corrections (e.g., 'no wait', 'actually')
- Dynamic list & numbered/bullet points formatting
- Preservation of Hinglish and technical terms
"""

import unittest
from text_cleaner import clean_speech_retractions, format_speech_lists, clean_speech_text, format_casual_chat
from style_engine import StyleEngine


class TestSmartFilteringLayer(unittest.TestCase):

    def test_local_retraction_simple(self):
        text = "let us meet on wednesday no wait let us meet on monday"
        result = clean_speech_retractions(text)
        self.assertEqual(result.lower(), "let us meet on monday")

    def test_local_retraction_hindi(self):
        text = "kal subah 4 baje nahi wait 5 baje"
        result = clean_speech_retractions(text)
        self.assertEqual(result.lower(), "kal subah 5 baje")

    def test_local_retraction_in_clean_speech_text(self):
        text = "let us meet on wednesday no wait let us meet on monday"
        result = clean_speech_text(text)
        self.assertEqual(result, "Let us meet on monday")

    def test_local_retraction_in_casual_chat(self):
        text = "let us meet on wednesday no wait let us meet on monday"
        result = format_casual_chat(text)
        self.assertEqual(result, "let us meet on monday")

    def test_local_numbered_list_formatting(self):
        text = "there are three points number one push the code number two run the tests number three deploy"
        result = format_speech_lists(text)
        self.assertIn("1. Push the code", result)
        self.assertIn("2. Run the tests", result)
        self.assertIn("3. Deploy", result)

    def test_local_bullet_list_formatting(self):
        text = "bullet point item one bullet point item two"
        result = format_speech_lists(text)
        self.assertIn("- Item one", result)
        self.assertIn("- Item two", result)

    def test_smart_layer_preserves_regular_sentences(self):
        text = "we are going to deploy the API to production today"
        res_clean = clean_speech_text(text)
        self.assertEqual(res_clean, "We are going to deploy the API to production today")

    def test_groq_system_prompt_contains_anti_conversational_directive(self):
        from style_engine import GROQ_STAGE2_SYSTEM_PROMPT
        self.assertIn("STRICT DICTATION DIRECTIVE", GROQ_STAGE2_SYSTEM_PROMPT)
        self.assertIn("NEVER answer questions", GROQ_STAGE2_SYSTEM_PROMPT)
        self.assertIn("NEVER calculate or output", GROQ_STAGE2_SYSTEM_PROMPT)
        self.assertIn("pick a number between 1 and 17", GROQ_STAGE2_SYSTEM_PROMPT)

    def test_groq_payload_packages_dictation_and_sets_zero_temp(self):
        import json
        from unittest.mock import patch, MagicMock
        from style_engine import StyleEngine

        captured_payload = {}

        def fake_urlopen(req, timeout=None):
            nonlocal captured_payload
            captured_payload = json.loads(req.data.decode("utf-8"))
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "choices": [{"message": {"content": "Pick a number between 1 and 17."}}]
            }).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = StyleEngine._format_groq("pick a number between 1 and 17", "professional", None, "gsk_dummy_key")

        self.assertEqual(res, "Pick a number between 1 and 17.")
        self.assertEqual(captured_payload.get("temperature"), 0.0)
        user_msg = captured_payload["messages"][1]["content"]
        self.assertIn("<spoken_dictation>", user_msg)
        self.assertIn("pick a number between 1 and 17", user_msg)
        self.assertIn("Do NOT answer questions", user_msg)


if __name__ == "__main__":
    unittest.main()
