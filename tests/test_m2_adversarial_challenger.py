"""
Adversarial Challenger Test Suite for Milestone M2:
Smart Voice Calibration & Phonetic Memory.

Challenger: Challenger M2-1 (critic, specialist)
Verification Goals:
1. Stress test PhoneticPairChip widgets, rapid confirm/dismiss actions, and profile persistence latency (<1ms).
2. Measure and verify VoiceTrainingDialog open latency (<50ms across multiple iterations, normal and bloated profile).
3. Test edge cases in calibration two-stage Romanization (code-mixed sentences, numbers, punctuation, zero-width joiners).
4. Verify dataset integrity and sentence #87 keyword contract.
"""

import sys
import os
import time
import json
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QHBoxLayout
from PySide6.QtCore import Qt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import calibration_engine
from voice_profile import VoiceProfileManager
from style_engine import FastDevanagariRomanizer
from benchmark_hinglish import reference_romanize_text, contains_devanagari
from ui.voice_training_dialog import PhoneticPairChip, VoiceTrainingDialog


class TestPhoneticPairChipStressAndPersistence(unittest.TestCase):
    """
    Adversarial Challenge 1:
    Stress test PhoneticPairChip widgets, rapid confirm/dismiss actions,
    and profile persistence latency (<1ms).
    """

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.profile_mgr = VoiceProfileManager.get_instance()
        # Clean test keys before each test
        self._test_keys = []

    def tearDown(self):
        for k in self._test_keys:
            try:
                self.profile_mgr.remove_replacement(k)
            except Exception:
                pass
            try:
                self.profile_mgr.remove_custom_word(k)
            except Exception:
                pass

    def test_profile_persistence_latency_sla(self):
        """Profile persistence latency: add_replacement and remove_replacement must be < 1ms."""
        num_iterations = 100
        add_latencies = []
        remove_latencies = []

        for i in range(num_iterations):
            key = f"stress_heard_{i}"
            val = f"stress_target_{i}"
            self._test_keys.append(key)

            t0 = time.perf_counter()
            self.profile_mgr.add_replacement(key, val)
            dt_add = (time.perf_counter() - t0) * 1000.0
            add_latencies.append(dt_add)

            t1 = time.perf_counter()
            self.profile_mgr.remove_replacement(key)
            dt_rem = (time.perf_counter() - t1) * 1000.0
            remove_latencies.append(dt_rem)

        mean_add = sum(add_latencies) / len(add_latencies)
        max_add = max(add_latencies)
        p95_add = sorted(add_latencies)[int(0.95 * len(add_latencies))]

        mean_rem = sum(remove_latencies) / len(remove_latencies)
        max_rem = max(remove_latencies)
        p95_rem = sorted(remove_latencies)[int(0.95 * len(remove_latencies))]

        print(f"\n[STRESS] add_replacement: mean={mean_add:.4f}ms, p95={p95_add:.4f}ms, max={max_add:.4f}ms")
        print(f"[STRESS] remove_replacement: mean={mean_rem:.4f}ms, p95={p95_rem:.4f}ms, max={max_rem:.4f}ms")

        # SLA requirement: Mean persistence latency < 1ms
        self.assertLess(mean_add, 1.0, f"Mean add_replacement latency {mean_add:.4f}ms exceeds 1ms SLA")
        self.assertLess(mean_rem, 1.0, f"Mean remove_replacement latency {mean_rem:.4f}ms exceeds 1ms SLA")

    def test_rapid_burst_chip_confirm_actions(self):
        """Stress test 50 rapid PhoneticPairChip confirm actions."""
        confirmed_records = []
        chips = []

        for i in range(50):
            h = f"misheard_{i}"
            t = f"Target_{i}"
            self._test_keys.append(h)

            def on_confirm(heard, target):
                confirmed_records.append((heard, target))

            chip = PhoneticPairChip(h, t, on_confirm=on_confirm)
            chips.append(chip)

        # Rapidly click confirm on all chips
        t0 = time.perf_counter()
        for chip in chips:
            chip.btn_confirm.click()
        elapsed_total = (time.perf_counter() - t0) * 1000.0
        per_chip_ms = elapsed_total / len(chips)

        print(f"\n[STRESS] Rapid confirm 50 chips: total={elapsed_total:.2f}ms, per_chip={per_chip_ms:.4f}ms")

        self.assertEqual(len(confirmed_records), 50)
        for i, chip in enumerate(chips):
            # Button must be disabled and text updated to '✓ Remembered'
            self.assertFalse(chip.btn_confirm.isEnabled())
            self.assertEqual(chip.btn_confirm.text(), "✓ Remembered")
            # Profile must contain the mapping
            h = f"misheard_{i}"
            t = f"Target_{i}"
            self.assertEqual(self.profile_mgr.get_replacements().get(h.lower()), t)

        # Idempotence: clicking disabled confirm button again should not error or double-trigger
        for chip in chips:
            chip.btn_confirm.click()
        self.assertEqual(len(confirmed_records), 50)

    def test_rapid_burst_chip_dismiss_actions(self):
        """Stress test 50 rapid PhoneticPairChip dismiss actions."""
        dismissed_records = []
        chips = []

        for i in range(50):
            h = f"misheard_dismiss_{i}"
            t = f"Target_dismiss_{i}"

            def on_dismiss(heard, target):
                dismissed_records.append((heard, target))

            chip = PhoneticPairChip(h, t, on_dismiss=on_dismiss)
            chip.show()
            chips.append(chip)

        t0 = time.perf_counter()
        for chip in chips:
            chip.btn_dismiss.click()
        elapsed_total = (time.perf_counter() - t0) * 1000.0

        print(f"\n[STRESS] Rapid dismiss 50 chips: total={elapsed_total:.2f}ms")

        self.assertEqual(len(dismissed_records), 50)
        for chip in chips:
            # Widget must be hidden
            self.assertTrue(chip.isHidden())

    def test_chip_with_none_callbacks_and_special_characters(self):
        """Chip must handle None callbacks and extreme characters safely without crashing."""
        special_pairs = [
            ("", ""),
            ("   ", "   "),
            ("cooper nets,.", "Kubernetes!"),
            ("123", "456"),
            ("pyside6@qt", "PySide6"),
            ("“quoted”", "unquoted"),
            ("main", "मैं"),
        ]

        for h, t in special_pairs:
            self._test_keys.append(h)
            chip = PhoneticPairChip(h, t, on_confirm=None, on_dismiss=None)
            self.assertIsNotNone(chip)
            # Confirm without crashing
            chip.btn_confirm.click()
            self.assertEqual(chip.btn_confirm.text(), "✓ Remembered")
            # Dismiss without crashing
            chip.btn_dismiss.click()
            self.assertTrue(chip.isHidden())


class TestVoiceTrainingDialogOpenLatency(unittest.TestCase):
    """
    Adversarial Challenge 2:
    Measure and verify VoiceTrainingDialog open latency (<50ms across multiple iterations).
    """

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.profile_mgr = VoiceProfileManager.get_instance()
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()

    def test_dialog_open_latency_20_iterations(self):
        """VoiceTrainingDialog instantiation latency across 20 runs must be strictly < 50ms."""
        latencies = []
        dialogs = []

        for i in range(20):
            t0 = time.perf_counter()
            dlg = VoiceTrainingDialog(self.mock_audio, self.mock_whisper)
            dt = (time.perf_counter() - t0) * 1000.0
            latencies.append(dt)
            dialogs.append(dlg)

        for d in dialogs:
            d.close()
            d.deleteLater()

        mean_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        p95_lat = sorted(latencies)[int(0.95 * len(latencies))]

        print(f"\n[LATENCY BENCHMARK] VoiceTrainingDialog Open (20 runs):")
        print(f"  Mean: {mean_lat:.2f}ms | Min: {min_lat:.2f}ms | Max: {max_lat:.2f}ms | p95: {p95_lat:.2f}ms")

        # Strict SLA check: Mean must be < 50ms, Max must be < 50ms
        self.assertLess(mean_lat, 50.0, f"Mean open latency {mean_lat:.2f}ms exceeds 50ms SLA")
        self.assertLess(max_lat, 50.0, f"Max open latency {max_lat:.2f}ms exceeds 50ms SLA")

    def test_dialog_open_latency_with_bloated_profile(self):
        """Dialog open latency must remain <50ms even when profile contains 200 words and 200 replacements."""
        initial_words_count = len(self.profile_mgr.get_custom_words())
        initial_reps_count = len(self.profile_mgr.get_replacements())

        # Inject 200 words and 200 replacements
        test_words = [f"custom_word_{i}" for i in range(200)]
        test_reps = {f"misheard_rule_{i}": f"target_rule_{i}" for i in range(200)}

        for w in test_words:
            self.profile_mgr.add_custom_word(w)
        for h, t in test_reps.items():
            self.profile_mgr.add_replacement(h, t)

        try:
            latencies = []
            dialogs = []
            for i in range(10):
                t0 = time.perf_counter()
                dlg = VoiceTrainingDialog(self.mock_audio, self.mock_whisper)
                dt = (time.perf_counter() - t0) * 1000.0
                latencies.append(dt)
                dialogs.append(dlg)

            mean_lat = sum(latencies) / len(latencies)
            max_lat = max(latencies)
            print(f"\n[BLOATED PROFILE] Open latency with 200 words + 200 rules (10 runs):")
            print(f"  Mean: {mean_lat:.2f}ms | Max: {max_lat:.2f}ms")

            self.assertLess(mean_lat, 50.0, f"Bloated profile open latency {mean_lat:.2f}ms exceeds 50ms SLA")

            # Verify navigating to review page deferred-loads row widgets properly
            test_dlg = dialogs[0]
            test_dlg._jump_to_review()
            self.assertEqual(test_dlg.word_list.count(), initial_words_count + 200)
            self.assertEqual(test_dlg.replacements_list.count(), initial_reps_count + 200)

            for d in dialogs:
                d.close()
                d.deleteLater()
        finally:
            # Cleanup bloated items
            for w in test_words:
                self.profile_mgr.remove_custom_word(w)
            for h in test_reps.keys():
                self.profile_mgr.remove_replacement(h)


class TestTwoStageRomanizationEdgeCases(unittest.TestCase):
    """
    Adversarial Challenge 3:
    Test edge cases in calibration two-stage Romanization
    (code-mixed sentences, numbers, punctuation, zero-width joiners).
    """

    def test_code_mixed_technical_sentences(self):
        """Code-mixed sentences must convert Devanagari to Romanized Hinglish while preserving English terms."""
        cases = [
            (
                "Docker कंटेनर रीस्टार्ट कर दिया but 500 एरर आ रहा है।",
                ["docker", "container", "restart", "kar", "diya", "but", "500", "error", "aa", "raha", "hai"]
            ),
            (
                "GitHub पर PR क्रिएट करके कमिट पुश कर दिया।",
                ["github", "par", "pr", "create", "karke", "commit", "push", "kar", "diya"]
            ),
            (
                "Main kal code push kar dunga.",
                ["main", "kal", "code", "push", "kar", "dunga"]
            ),
            (
                "Client ko presentation demo dikhana hai afternoon mein.",
                ["client", "ko", "presentation", "demo", "dikhana", "hai", "afternoon", "mein"]
            ),
        ]

        for dev_input, expected_keywords in cases:
            res = FastDevanagariRomanizer.romanize(dev_input)
            self.assertFalse(
                FastDevanagariRomanizer.has_devanagari(res),
                f"Romanization output still contains Devanagari: {res}"
            )
            res_lower = res.lower()
            for kw in expected_keywords:
                self.assertIn(kw.lower(), res_lower, f"Keyword '{kw}' missing from Romanized output '{res}'")

    def test_phonetic_memory_pipeline_on_devanagari_transcriptions(self):
        """
        Verify that when Whisper outputs Devanagari phonetics for technical jargon,
        two-stage Romanization produces clean Latin diffing and extracts target phonetic pairs.
        """
        target = "Kubernetes cluster mein pod crashloopbackoff state mein chala gaya."
        whisper_devanagari = "कुबरनेट्स क्लस्टर में पॉड क्रैश लूप बैक ऑफ स्टेट में चला गया।"

        romanized = FastDevanagariRomanizer.romanize(whisper_devanagari)
        self.assertFalse(FastDevanagariRomanizer.has_devanagari(romanized))

        diff_res = calibration_engine.compute_diff(target, romanized, ["cluster", "Kubernetes"])
        misheard = diff_res.get("misheard_pairs", [])

        # The diff engine must extract misheard pairs (e.g. kubrnets -> Kubernetes, klastar -> cluster)
        self.assertTrue(len(misheard) >= 2)
        heard_words = [p["heard"].lower() for p in misheard]
        target_words = [p["target"].lower() for p in misheard]

        self.assertIn("kubernetes", target_words)
        self.assertIn("cluster", target_words)

        # Confirm that 1-click confirmation chip on these pairs immediately commits to profile
        profile_mgr = VoiceProfileManager.get_instance()
        chip = PhoneticPairChip(misheard[0]["heard"], misheard[0]["target"])
        chip.btn_confirm.click()
        self.assertEqual(
            profile_mgr.get_replacements().get(misheard[0]["heard"].lower()),
            misheard[0]["target"]
        )

        # Clean up
        profile_mgr.remove_replacement(misheard[0]["heard"])

    def test_devanagari_numerals_and_mixed_digits(self):
        """Devanagari digits (०-९) and mixed numbers must Romanize cleanly."""
        cases = [
            ("०१२३४५६७८९", "0123456789"),
            ("सर्वर ५ मिनट में रीस्टार्ट होगा", "server 5 minute mein restart hoga"),
            ("हमने २ घंटे काम किया और १०० फाइल्स चेक की", ["2", "ghante", "100", "files", "check"]),
            ("Port 8080 पर ट्रैफिक आ रहा है", ["port", "8080", "traffic"]),
        ]

        for text, expectation in cases:
            res = FastDevanagariRomanizer.romanize(text)
            self.assertFalse(FastDevanagariRomanizer.has_devanagari(res))
            if isinstance(expectation, str):
                self.assertIn(expectation.lower(), res.lower())
            elif isinstance(expectation, list):
                for token in expectation:
                    self.assertIn(token.lower(), res.lower())

    def test_complex_punctuation_and_dandas(self):
        """Punctuation including Danda, Double Danda, ellipses, quotes, and symbols."""
        cases = [
            ("मैं कल आऊंगा।", ["main", "kal"]),
            ("नमस्ते॥", "namaste."),
            ("“क्या तुम कल आओगे?”", "kya tum kal aaoge"),
            ("रुको... सोचो!", "ruko... socho!"),
            ("डेटाबेस; माइग्रेशन: कम्प्लीट!", ["database", "migration", "complete"]),
        ]

        for text, expected in cases:
            res = FastDevanagariRomanizer.romanize(text)
            self.assertFalse(FastDevanagariRomanizer.has_devanagari(res))
            if isinstance(expected, str):
                self.assertIn(expected.lower().replace(".", "").replace("!", "").strip(), res.lower().replace(".", "").replace("!", "").strip())
            else:
                for exp in expected:
                    self.assertIn(exp.lower(), res.lower())

    def test_zero_width_joiners_and_combining_marks(self):
        """Zero-width joiners (ZWJ/ZWNJ) and rare combining marks must not corrupt Romanization."""
        # \u200c = ZERO WIDTH NON-JOINER, \u200d = ZERO WIDTH JOINER
        text_with_zwj = "क\u200d्\u200cया आप कल आएँगे?"
        res = FastDevanagariRomanizer.romanize(text_with_zwj)
        self.assertFalse(FastDevanagariRomanizer.has_devanagari(res))
        self.assertNotIn("\u200c", res)
        self.assertNotIn("\u200d", res)

    def test_compute_diff_with_romanized_edge_cases(self):
        """compute_diff produces clean misheard pairs and high accuracy with Romanized edge cases."""
        # Edge Case 1: Target has numbers and punctuation, Whisper transcribes in Devanagari with Danda
        target = "Server 5 minute mein restart hoga."
        heard_devanagari = "सर्वर ५ मिनट में रीस्टार्ट होगा।"
        heard_romanized = FastDevanagariRomanizer.romanize(heard_devanagari)

        diff_res = calibration_engine.compute_diff(target, heard_romanized)
        self.assertGreaterEqual(diff_res["accuracy"], 80.0)

        # Edge Case 2: Misheard word extraction with messy punctuation
        target2 = "Client ko demo dikhane se pehle edge cases thoroughly test kar lena."
        heard2 = "Client ko daemo, dikhane se pehle edge cases thoroly. test kar lena."
        diff_res2 = calibration_engine.compute_diff(target2, heard2, ["demo", "thoroughly"])
        pairs = diff_res2["misheard_pairs"]

        self.assertTrue(len(pairs) > 0)
        for p in pairs:
            # Trailing punctuation must be stripped
            self.assertFalse(p["heard"].endswith(","))
            self.assertFalse(p["heard"].endswith("."))
            self.assertFalse(p["target"].endswith(","))
            self.assertFalse(p["target"].endswith("."))

    def test_sentence_87_authoritative_contract(self):
        """Sentence #87 in data/calibration_sentences.json has keyword 'demo' and Romanized text."""
        dataset_path = os.path.join(PROJECT_ROOT, "data", "calibration_sentences.json")
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        s87 = next((s for s in dataset if s["id"] == 87), None)
        self.assertIsNotNone(s87, "Sentence #87 not found in calibration_sentences.json")
        self.assertEqual(s87["category"], "hindi_hinglish")
        self.assertEqual(s87["text"], "Client ko demo dikhane se pehle edge cases thoroughly test kar lena.")
        self.assertIn("demo", s87["phonetic_keywords"])
        self.assertFalse(FastDevanagariRomanizer.has_devanagari(s87["text"]))


if __name__ == "__main__":
    unittest.main()
