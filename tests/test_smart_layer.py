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


if __name__ == "__main__":
    unittest.main()
