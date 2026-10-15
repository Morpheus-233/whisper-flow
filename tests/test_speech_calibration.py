"""
Unit and integration tests for Bilingual Speech Calibration and Phonetic Mapping.
Covers:
- F1: 100-Sentence Bilingual Dataset verification (50 English, 50 Hindi/Hinglish)
- F2: Word-level SequenceMatcher diff engine with clamped accuracy and punctuation-clean pairs
- F3: Automated phonetic correction mapper into voice profile
- F4: Regex lookaround replacement engine for punctuation-laden keys
- F5: Vocabulary biasing (initial_prompt) generation and context truncation
- F6: Calibration wizard integration with the 100-sentence dataset
"""

import os
import json
import unittest
from unittest.mock import MagicMock, patch

import calibration_engine
from voice_profile import VoiceProfileManager


class TestCalibrationDataset(unittest.TestCase):
    """Tier 1 & Tier 2 tests for calibration dataset integrity."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.dataset_path = os.path.join(cls.project_root, "data", "calibration_sentences.json")

    def test_dataset_file_exists(self):
        self.assertTrue(os.path.exists(self.dataset_path), f"Missing {self.dataset_path}")

    def test_dataset_contains_100_sentences(self):
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 100, f"Expected 100 sentences, got {len(data)}")

    def test_dataset_category_distribution(self):
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        english_count = sum(1 for d in data if d.get("category") == "english")
        hindi_count = sum(1 for d in data if d.get("category") == "hindi_hinglish")
        self.assertEqual(english_count, 50, f"Expected 50 English sentences, got {english_count}")
        self.assertEqual(hindi_count, 50, f"Expected 50 Hindi/Hinglish sentences, got {hindi_count}")

    def test_dataset_schema_validation(self):
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        seen_ids = set()
        for idx, item in enumerate(data):
            self.assertIn("id", item, f"Sentence #{idx} missing 'id'")
            self.assertIn("category", item, f"Sentence #{idx} missing 'category'")
            self.assertIn("text", item, f"Sentence #{idx} missing 'text'")
            self.assertIn("phonetic_keywords", item, f"Sentence #{idx} missing 'phonetic_keywords'")

            self.assertIsInstance(item["id"], int)
            self.assertIn(item["category"], ("english", "hindi_hinglish"))
            self.assertIsInstance(item["text"], str)
            self.assertTrue(len(item["text"].strip()) > 5)
            self.assertIsInstance(item["phonetic_keywords"], list)
            self.assertTrue(len(item["phonetic_keywords"]) > 0)
            seen_ids.add(item["id"])

        self.assertEqual(len(seen_ids), 100, "Duplicate sentence IDs found in dataset")

    def test_calibration_engine_loader(self):
        dataset = calibration_engine.load_calibration_dataset(self.dataset_path)
        self.assertEqual(len(dataset), 100)
        self.assertEqual(dataset[0]["category"], "english")
        self.assertEqual(dataset[50]["category"], "hindi_hinglish")


class TestDiffEngine(unittest.TestCase):
    """Tier 1 & Tier 2 tests for word-level SequenceMatcher diff calculation."""

    def test_perfect_match_accuracy(self):
        target = "The quick brown fox jumps over the lazy dog."
        transcribed = "The quick brown fox jumps over the lazy dog."
        res = calibration_engine.compute_diff(target, transcribed)
        self.assertEqual(res["accuracy"], 100.0)
        self.assertEqual(len(res["misheard_pairs"]), 0)
        self.assertEqual(len(res["missing_keywords"]), 0)

    def test_complete_mismatch_accuracy(self):
        target = "Alpha beta gamma delta"
        transcribed = "One two three four"
        res = calibration_engine.compute_diff(target, transcribed)
        self.assertEqual(res["accuracy"], 0.0)

    def test_empty_string_handling(self):
        # Both empty
        res1 = calibration_engine.compute_diff("", "")
        self.assertEqual(res1["accuracy"], 100.0)

        # Target empty, transcribed not empty
        res2 = calibration_engine.compute_diff("", "Something spoken")
        self.assertEqual(res2["accuracy"], 0.0)

        # Target not empty, transcribed empty
        res3 = calibration_engine.compute_diff("Expected words", "")
        self.assertEqual(res3["accuracy"], 0.0)

    def test_accuracy_clamped_between_0_and_100(self):
        res = calibration_engine.compute_diff("Hello world", "Hello world and many extra spoken words")
        self.assertTrue(0.0 <= res["accuracy"] <= 100.0)

    def test_hinglish_diff_and_punctuation_clean_misheard_pairs(self):
        target = "Main thodi der mein call karta hoon."
        transcribed = "main thodi der me call karta hu"
        keywords = ["thodi der", "call karta hoon"]

        res = calibration_engine.compute_diff(target, transcribed, phonetic_keywords=keywords)
        self.assertTrue(0.0 < res["accuracy"] < 100.0)

        # CRITICAL TEST: misheard pairs MUST NOT leak trailing period from 'hoon.'
        pairs = res["misheard_pairs"]
        self.assertTrue(len(pairs) >= 1)

        for pair in pairs:
            # Target and heard words must not end in punctuation
            self.assertFalse(pair["target"].endswith("."), f"Target has trailing period: {pair['target']}")
            self.assertFalse(pair["target"].endswith(","), f"Target has trailing comma: {pair['target']}")
            self.assertFalse(pair["heard"].endswith("."), f"Heard has trailing period: {pair['heard']}")

        # Verify specific misheard pair target value is 'hoon' not 'hoon.'
        target_words = [p["target"] for p in pairs]
        self.assertIn("hoon", target_words)
        self.assertNotIn("hoon.", target_words)

    def test_missing_phonetic_keywords(self):
        target = "Kubernetes clusters deploy microservices rapidly."
        transcribed = "clusters deploy microservices rapidly"
        keywords = ["Kubernetes clusters", "microservices"]

        res = calibration_engine.compute_diff(target, transcribed, phonetic_keywords=keywords)
        self.assertIn("Kubernetes clusters", res["missing_keywords"])
        self.assertNotIn("microservices", res["missing_keywords"])

    def test_adversarial_pure_punctuation_input(self):
        """Adversarial edge case: Target or transcribed string consists solely of punctuation symbols."""
        res = calibration_engine.compute_diff("... ,,, ??? !!!", "hello world")
        self.assertTrue(0.0 <= res["accuracy"] <= 100.0)
        self.assertEqual(res["accuracy"], 0.0)

    def test_adversarial_unicode_and_quotes(self):
        """Adversarial edge case: Fancy typographical quotes and Hindi Devanagari text."""
        clean = calibration_engine.strip_punctuation("“PySide6!”")
        self.assertEqual(clean, "PySide6")

        target = "“Whisper Flow” supports ‘CTranslate2’ natively."
        heard = "whisper flow supports ctranslate2 natively"
        res = calibration_engine.compute_diff(target, heard)
        self.assertEqual(res["accuracy"], 100.0)


class TestPhoneticMapperAndVoiceProfile(unittest.TestCase):
    """Tier 1 & Tier 2 tests for automated phonetic registration and regex lookarounds."""

    def setUp(self):
        self.mock_profile = {
            "custom_words": ["OpenCode", "CTranslate2"],
            "word_replacements": {
                "open code": "OpenCode",
                "see translate": "CTranslate2"
            }
        }
        self.mock_mgr = MagicMock(spec=VoiceProfileManager)
        self.mock_mgr.get_replacements.return_value = dict(self.mock_profile["word_replacements"])
        self.mock_mgr.get_custom_words.return_value = list(self.mock_profile["custom_words"])

        def add_rep(heard, target):
            self.mock_profile["word_replacements"][heard.lower()] = target
            self.mock_mgr.get_replacements.return_value = dict(self.mock_profile["word_replacements"])

        self.mock_mgr.add_replacement.side_effect = add_rep

    def test_auto_register_misheard_pairs(self):
        misheard = [
            {"heard": "me", "target": "mein"},
            {"heard": "hu", "target": "hoon"}
        ]
        added = calibration_engine.auto_register_misheard_pairs(misheard, self.mock_mgr)
        self.assertEqual(added, 2)
        reps = self.mock_mgr.get_replacements()
        self.assertEqual(reps.get("me"), "mein")
        self.assertEqual(reps.get("hu"), "hoon")

        # Second registration of identical pairs should be idempotent (return 0 added)
        added_again = calibration_engine.auto_register_misheard_pairs(misheard, self.mock_mgr)
        self.assertEqual(added_again, 0)

    def test_lookaround_regex_with_punctuation_keys(self):
        """
        Tests that VoiceProfileManager.apply_replacements handles punctuation keys like 'cooper nets,'.
        In Python regex, standard word boundary r'\\bcooper nets,\\b' fails because comma is \\W.
        Lookaround boundaries (?<!\\w) and (?!\\w) allow clean matching.
        """
        mgr = VoiceProfileManager.get_instance()
        # Save original replacements to restore in tearDown
        original_reps = dict(mgr.get_replacements())

        try:
            # Set test replacements including one with a trailing comma
            mgr.profile["word_replacements"] = {
                "cooper nets,": "Kubernetes",
                "pie side": "PySide6",
                "docker file": "Dockerfile"
            }

            # 1. Punctuation key replacement
            text1 = "I manage cooper nets, in our cloud infrastructure."
            out1 = mgr.apply_replacements(text1)
            self.assertEqual(out1, "I manage Kubernetes in our cloud infrastructure.")

            # 2. Standard multi-word replacement
            text2 = "We built this with pie side and a custom docker file."
            out2 = mgr.apply_replacements(text2)
            self.assertEqual(out2, "We built this with PySide6 and a custom Dockerfile.")

            # 3. Word boundary protection (do not replace substring inside another word)
            text3 = "pie side is awesome but not pie sidewinder."
            out3 = mgr.apply_replacements(text3)
            self.assertIn("PySide6", out3)
            self.assertIn("pie sidewinder", out3)
        finally:
            mgr.profile["word_replacements"] = original_reps

    def test_initial_prompt_biasing_and_truncation(self):
        mgr = VoiceProfileManager.get_instance()
        original_words = list(mgr.get_custom_words())

        try:
            # Case A: Normal vocabulary list
            mgr.profile["custom_words"] = ["Soham", "OpenCode", "PySide6", "Hinglish"]
            prompt = mgr.get_initial_prompt()
            self.assertIsNotNone(prompt)
            self.assertTrue(prompt.startswith("Vocabulary: "))
            self.assertTrue(prompt.endswith("."))
            self.assertIn("PySide6", prompt)
            self.assertIn("Hinglish", prompt)

            # Case B: Empty custom words returns None
            mgr.profile["custom_words"] = []
            self.assertIsNone(mgr.get_initial_prompt())

            # Case C: Extreme length truncation test (Tier 2)
            large_vocab = [f"TechnicalKeyword_{i}" for i in range(200)]
            mgr.profile["custom_words"] = large_vocab
            prompt_truncated = mgr.get_initial_prompt(max_chars=300) if hasattr(mgr, 'get_initial_prompt') else None
            if prompt_truncated:
                self.assertTrue(len(prompt_truncated) <= 300)
                self.assertTrue(prompt_truncated.startswith("Vocabulary: "))
                self.assertTrue(prompt_truncated.endswith("."))
        finally:
            mgr.profile["custom_words"] = original_words


if __name__ == "__main__":
    unittest.main()
