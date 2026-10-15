"""
Adversarial Empirical Stress Harness for Milestone 1.
Author: Challenger 1 (Milestone 1 Empirical Challenger)

Tests empirical edge cases, stress boundaries, failure modes, and invariants in:
- calibration_engine.py (diffing, tokenization, punctuation stripping, dataset loading, auto-registration)
- voice_profile.py (lookaround regex substitutions, prefix protection, initial_prompt generation, scalability)
"""

import os
import sys
import json
import time
import re
import unittest
from unittest.mock import MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import calibration_engine
from voice_profile import VoiceProfileManager


class TestEmpiricalDiffStress(unittest.TestCase):
    """Stress tests and boundary exploration for calibration_engine.compute_diff."""

    def test_empty_and_whitespace_inputs(self):
        # 1. Both empty
        r = calibration_engine.compute_diff("", "")
        self.assertEqual(r["accuracy"], 100.0)
        self.assertEqual(r["diff"], [])
        self.assertEqual(r["misheard_pairs"], [])

        # 2. Whitespace variants
        r2 = calibration_engine.compute_diff("   \t  \n  ", "  \n  ")
        self.assertEqual(r2["accuracy"], 100.0)

        # 3. Target empty, heard non-empty (100% insertion)
        r3 = calibration_engine.compute_diff("", "hello world")
        self.assertEqual(r3["accuracy"], 0.0)
        self.assertEqual(len(r3["diff"]), 1)
        self.assertEqual(r3["diff"][0]["type"], "insert")
        self.assertEqual(r3["diff"][0]["heard"], "hello world")

        # 4. Target non-empty, heard empty (100% deletion)
        r4 = calibration_engine.compute_diff("hello world", "")
        self.assertEqual(r4["accuracy"], 0.0)
        self.assertEqual(len(r4["diff"]), 1)
        self.assertEqual(r4["diff"][0]["type"], "delete")
        self.assertEqual(r4["diff"][0]["target"], "hello world")

    def test_completely_disjoint_sentences(self):
        target = "The quick brown fox jumps over the lazy dog"
        heard = "Quantum entanglement governs cryptographic key distribution"
        r = calibration_engine.compute_diff(target, heard)
        self.assertEqual(r["accuracy"], 0.0)
        self.assertTrue(0.0 <= r["accuracy"] <= 100.0)
        self.assertTrue(len(r["diff"]) > 0)

    def test_repeated_tokens_and_asymmetric_lengths(self):
        # Target: single token, Heard: token repeated 100 times
        target = "word"
        heard = " ".join(["word"] * 100)
        r = calibration_engine.compute_diff(target, heard)
        # Denominator should be max(1, 100) = 100. Matches = 1. Accuracy = 1.0%
        self.assertEqual(r["accuracy"], 1.0)

        # Target: token repeated 100 times, Heard: single token
        target2 = " ".join(["word"] * 100)
        heard2 = "word"
        r2 = calibration_engine.compute_diff(target2, heard2)
        self.assertEqual(r2["accuracy"], 1.0)

    def test_m_to_n_phrase_replacements(self):
        # 1 to 2 tokens
        r1 = calibration_engine.compute_diff("Kubernetes", "cooper nets")
        self.assertEqual(len(r1["misheard_pairs"]), 1)
        self.assertEqual(r1["misheard_pairs"][0], {"heard": "cooper nets", "target": "Kubernetes"})

        # 3 to 1 tokens
        r2 = calibration_engine.compute_diff("CI CD pipeline", "cicd")
        self.assertEqual(len(r2["misheard_pairs"]), 1)
        self.assertEqual(r2["misheard_pairs"][0], {"heard": "cicd", "target": "CI CD pipeline"})

        # 3 to 2 tokens
        r3 = calibration_engine.compute_diff("high performance computing", "fast math")
        self.assertEqual(len(r3["misheard_pairs"]), 1)
        self.assertEqual(r3["misheard_pairs"][0], {"heard": "fast math", "target": "high performance computing"})

    def test_high_volume_tokens_performance(self):
        # 500 identical tokens
        words = ["token"] * 500
        text = " ".join(words)
        t0 = time.time()
        r = calibration_engine.compute_diff(text, text)
        duration = time.time() - t0
        self.assertEqual(r["accuracy"], 100.0)
        self.assertLess(duration, 0.5, f"Diffing 500 tokens took too long: {duration:.3f}s")

    def test_pure_punctuation_false_equality_vulnerability(self):
        """
        Adversarial test:
        If both target and heard contain only punctuation symbols, clean_token reduces
        both to empty strings [""], causing SequenceMatcher to treat them as EQUAL.
        Target: '...' vs Heard: '???'
        """
        r = calibration_engine.compute_diff("...", "???")
        # Punctuation strings with completely different symbols should NOT be equal!
        is_vulnerable = (r["accuracy"] == 100.0)
        print(f"\n[FINDING] Pure punctuation diff('...', '???') accuracy: {r['accuracy']}% (vulnerable: {is_vulnerable})")
        self.assertFalse(is_vulnerable, "Pure punctuation mismatch must not be 100% equal")
        self.assertEqual(r["accuracy"], 0.0, "Pure punctuation mismatch must return 0.0% accuracy")


class TestPunctuationStrippingEdgeCases(unittest.TestCase):
    """Adversarial stress tests for calibration_engine.strip_punctuation and clean_token."""

    def test_nested_and_typographical_punctuation(self):
        cases = [
            ("“‘[((NESTED))]’‘”", "NESTED"),
            ("‘single-quote’", "single-quote"),
            ("«guillemets»", "guillemets"),
            ("¿que?", "que"),
            ("¡hola!", "hola"),
            ("...ellipsis...", "ellipsis"),
            ("---dashes---", "dashes"),
            ("***asterisks***", "asterisks"),
            ("###hashes###", "hashes"),
            ("```code```", "code"),
            ("don't", "don't"),
            ("semi;colon:", "semi;colon"),
        ]
        for inp, expected in cases:
            res = calibration_engine.strip_punctuation(inp)
            self.assertEqual(res, expected, f"Failed on input: {inp} -> got {res!r}, expected {expected!r}")

    def test_devanagari_vowel_sign_truncation_vulnerability(self):
        """
        Adversarial test:
        Python regex r'[^\w\s]' treats Unicode non-spacing marks (Mn / Mc) as non-alphanumeric,
        causing strip_punctuation and clean_token to mutilate Hindi words ending in vowel marks.
        """
        hindi_words = {
            "नमस्ते": "namaste (ends in e-matra \\u0947)",
            "करो": "karo (ends in o-matra \\u094b)",
            "मेरी": "meri (ends in ii-matra \\u0940)",
            "पैसा": "paisa (ends in aa-matra \\u093e)",
            "हैं": "hain (ends in ai-matra \\u0948 and anusvara \\u0902)",
            "नहीं": "nahin (ends in ii-matra \\u0940 and anusvara \\u0902)",
        }
        mutilated = []
        for word, desc in hindi_words.items():
            cleaned = calibration_engine.strip_punctuation(word)
            if cleaned != word:
                mutilated.append((word, cleaned, desc))

        print(f"\n[FINDING] Devanagari vowel truncation: {len(mutilated)}/{len(hindi_words)} words mutilated!")
        for orig, cln, d in mutilated:
            print(f"  - Original: '{orig}' -> Mutilated: '{cln}' ({d})")
        self.assertEqual(len(mutilated), 0, f"Devanagari vowel signs must not be truncated: {mutilated}")

        # In clean_token:
        # 'कर' (kar) and 'करो' (karo) must be preserved as distinct tokens
        ct_kar = calibration_engine.clean_token("कर")
        ct_karo = calibration_engine.clean_token("करो")
        self.assertNotEqual(ct_kar, ct_karo, "clean_token must distinguish 'कर' and 'करो'!")

        # In compute_diff:
        diff_res = calibration_engine.compute_diff("कर", "करो")
        self.assertNotEqual(diff_res["accuracy"], 100.0, "diff must not give 100% accuracy for different Hindi words!")
        self.assertEqual(diff_res["accuracy"], 0.0, "diff should report 0.0% accuracy for distinct Hindi words")

    def test_misheard_pairs_punctuation_cleanliness(self):
        """Ensures that no misheard pair registered from noisy text contains leading/trailing punctuation."""
        target = "«PySide6!», “CTranslate2;”, [OpenCode?], and 'PostgreSQL.'."
        heard = "pie side, see translate, open code, and postgres"
        r = calibration_engine.compute_diff(target, heard)
        pairs = r["misheard_pairs"]
        self.assertTrue(len(pairs) > 0)
        for pair in pairs:
            t = pair["target"]
            h = pair["heard"]
            self.assertFalse(re.search(r"^[^\w]+|[^\w]+$", t), f"Target has boundary punctuation: {t!r}")
            self.assertFalse(re.search(r"^[^\w]+|[^\w]+$", h), f"Heard has boundary punctuation: {h!r}")


class TestVoiceProfileLookaroundStress(unittest.TestCase):
    """Adversarial stress tests for VoiceProfileManager.apply_replacements and initial_prompt."""

    def setUp(self):
        self.mgr = VoiceProfileManager.get_instance()
        self.original_reps = dict(self.mgr.get_replacements())
        self.original_words = list(self.mgr.get_custom_words())

    def tearDown(self):
        self.mgr.profile["word_replacements"] = self.original_reps
        self.mgr.profile["custom_words"] = self.original_words

    def test_lookaround_boundary_protection(self):
        """Ensures replacement doesn't trigger on substrings of longer words."""
        self.mgr.profile["word_replacements"] = {
            "cat": "feline",
            "pie side": "PySide6",
            "dock": "wharf"
        }
        text = "The category of docker is scattered, but pie sidewinder saw a cat on the dock."
        out = self.mgr.apply_replacements(text)

        # "cat" must not replace inside "category" or "scattered"
        self.assertIn("category", out)
        self.assertIn("scattered", out)
        # "pie side" must not replace inside "pie sidewinder"
        self.assertIn("pie sidewinder", out)
        # "dock" must not replace inside "docker"
        self.assertIn("docker", out)
        # Standalone "cat" and "dock" must replace
        self.assertIn("feline", out)
        self.assertIn("wharf", out)

    def test_special_regex_characters_in_replacement_keys(self):
        """Keys containing regex metacharacters: +, *, ?, (, ), [, ], ^, $, |, \\."""
        self.mgr.profile["word_replacements"] = {
            "c++": "C++ Programming",
            "c#": "C-Sharp",
            "[core]": "Core System",
            "a+b": "Addition",
            "x*y": "Multiplication",
            "(test)": "Examination",
            "foo|bar": "FooBar"
        }
        text = "I love c++ and c# with [core] module doing a+b and x*y during (test) with foo|bar."
        out = self.mgr.apply_replacements(text)
        self.assertEqual(out, "I love C++ Programming and C-Sharp with Core System module doing Addition and Multiplication during Examination with FooBar.")

    def test_devanagari_right_boundary_lookahead_bug(self):
        """
        Adversarial test:
        In voice_profile.py line 173:
        rb = r'(?!\w)' if (k[-1].isalnum() or k[-1] == '_') else ''
        For Hindi words ending in a vowel sign (like 'ो', 'े', 'ा'), k[-1].isalnum() is False.
        Therefore, rb is empty '', allowing the key to match as a prefix inside longer Hindi words!
        """
        self.mgr.profile["word_replacements"] = {
            "करो": "karo",
            "नमस्ते": "Namaste"
        }
        # In 'करोगे तो पाओगे', 'करो' should NOT match inside 'करोगे'!
        out = self.mgr.apply_replacements("करोगे तो पाओगे")
        is_buggy = (out == "karoगे तो पाओगे")
        print(f"\n[FINDING] Devanagari prefix replacement bug: 'करोगे' -> {out!r} (bug present: {is_buggy})")
        self.assertFalse(is_buggy, "Devanagari prefix replacement bug must not be present")
        self.assertEqual(out, "करोगे तो पाओगे")

        # In 'नमस्तेजी', 'नमस्ते' should NOT match inside 'नमस्तेजी'!
        out2 = self.mgr.apply_replacements("नमस्तेजी")
        print(f"  - 'नमस्तेजी' -> {out2!r}")
        self.assertEqual(out2, "नमस्तेजी")

    def test_large_scale_regex_throughput_and_no_catastrophic_backtracking(self):
        """Stress-tests 2,000 replacement rules against a 10,000-token text."""
        num_rules = 2000
        self.mgr.profile["word_replacements"] = {
            f"misheard phrase {i}": f"TargetKeyword_{i}" for i in range(num_rules)
        }
        # Add special chars and punctuation keys
        self.mgr.profile["word_replacements"]["cooper nets,"] = "Kubernetes"
        self.mgr.profile["word_replacements"]["c++"] = "C++"

        test_tokens = [f"misheard phrase {i}" if i % 5 == 0 else f"token_{i}" for i in range(1000)]
        test_text = " ".join(test_tokens) + " and cooper nets, with c++."

        t0 = time.time()
        result = self.mgr.apply_replacements(test_text)
        duration = time.time() - t0

        self.assertIn("Kubernetes", result)
        self.assertIn("C++", result)
        self.assertIn("TargetKeyword_0", result)
        self.assertLess(duration, 2.0, f"Regex replacement with 2000 rules was too slow: {duration:.3f}s")
        print(f"\n[BENCHMARK] apply_replacements (2000 rules, 1000 tokens): {duration:.4f}s")

    def test_initial_prompt_stress_and_strict_char_budget(self):
        """Tests that initial_prompt strictly obeys character limits across edge case inputs."""
        # 1. Zero words
        self.mgr.profile["custom_words"] = []
        self.assertIsNone(self.mgr.get_initial_prompt())

        # 2. Whitespace-only words
        self.mgr.profile["custom_words"] = ["   ", "", "\t"]
        self.assertIsNone(self.mgr.get_initial_prompt())

        # 3. Budget strictly smaller than prefix + suffix (prefix 'Vocabulary: ' is 12 chars, suffix '.' is 1 char)
        self.mgr.profile["custom_words"] = ["OpenCode", "PySide6"]
        self.assertIsNone(self.mgr.get_initial_prompt(max_chars=12))
        self.assertIsNone(self.mgr.get_initial_prompt(max_chars=13))

        # 4. Exact fit test
        # "Vocabulary: AI." -> 12 + 2 + 1 = 15 chars
        self.mgr.profile["custom_words"] = ["AI", "ML"]
        p15 = self.mgr.get_initial_prompt(max_chars=15)
        self.assertEqual(p15, "Vocabulary: AI.")
        self.assertEqual(len(p15), 15)

        # 5. Massive vocabulary truncation
        self.mgr.profile["custom_words"] = [f"Word_{i:04d}" for i in range(500)]
        p800 = self.mgr.get_initial_prompt(max_chars=800)
        self.assertIsNotNone(p800)
        self.assertLessEqual(len(p800), 800)
        self.assertTrue(p800.startswith("Vocabulary: "))
        self.assertTrue(p800.endswith("."))


class TestAutoRegisterIdempotenceAndPersistence(unittest.TestCase):
    """Tests auto-registration idempotence, casing handling, and profile persistence."""

    def test_idempotence_and_case_deduplication(self):
        mock_profile = {"word_replacements": {"me": "mein"}}
        mock_mgr = MagicMock()
        mock_mgr.get_replacements.return_value = dict(mock_profile["word_replacements"])

        def add_rep(h, t):
            mock_profile["word_replacements"][h.lower()] = t
            mock_mgr.get_replacements.return_value = dict(mock_profile["word_replacements"])

        mock_mgr.add_replacement.side_effect = add_rep

        pairs = [
            {"heard": "me", "target": "mein"},  # Already present -> skip
            {"heard": "ME", "target": "mein"},  # Upper case equivalent -> skip
            {"heard": "hu", "target": "hoon"},  # New -> add
            {"heard": "hu.", "target": "hoon."}, # With punctuation -> should be stripped to 'hu' -> skip
        ]

        added = calibration_engine.auto_register_misheard_pairs(pairs, mock_mgr)
        self.assertEqual(added, 1, f"Expected 1 newly added pair, got {added}")
        self.assertEqual(mock_profile["word_replacements"]["hu"], "hoon")


if __name__ == "__main__":
    unittest.main()
