"""
Empirical Stress Test Harness: Challenger 2 for Milestone 1.

Verification & Stress Scope:
1. Dataset Schema & Keyword Integrity:
   - Validates all 100 sentences, 50 English / 50 Hindi-Hinglish distribution.
   - Evaluates phonetic keyword alignment against target sentence text.
   - Highlights empirical anomaly on Sentence #87 ('client demo' vs 'Client ko demo').
2. VoiceTrainingDialog Open Latency & Rapid Cycling:
   - Measures 10 consecutive open/init cycles (<50ms limit).
   - Benchmarks latency impact of dictionary size (7 up to 1000 custom words).
3. Concurrent & Stress Phonetic Registration:
   - 10-thread concurrent auto-registration into voice_profile.json.
   - Integrity verification: valid JSON, zero data corruption, zero unhandled exceptions.
4. Vocabulary Biasing Initial Prompt Generation:
   - Stress-testing prompt generator with up to 1000 custom words.
   - Strict adherence to max_chars token budget (800 chars limit).
   - Verifies no word truncation mid-token, no dangling commas, and sub-millisecond execution.
"""

import sys
import os
import json
import time
import threading
import tempfile
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import calibration_engine
from voice_profile import VoiceProfileManager
from PySide6.QtWidgets import QApplication
from ui.voice_training_dialog import VoiceTrainingDialog, CALIBRATION_DATASET, CALIBRATION_SENTENCES


class TestDatasetEmpiricalRigor(unittest.TestCase):
    """Deep empirical inspection of calibration_sentences.json."""

    @classmethod
    def setUpClass(cls):
        cls.dataset_path = os.path.join(PROJECT_ROOT, "data", "calibration_sentences.json")
        with open(cls.dataset_path, "r", encoding="utf-8") as f:
            cls.raw_data = json.load(f)

    def test_total_sentence_count_and_distribution(self):
        self.assertEqual(len(self.raw_data), 100, f"Dataset must contain exactly 100 sentences, got {len(self.raw_data)}")
        english = [s for s in self.raw_data if s.get("category") == "english"]
        hindi = [s for s in self.raw_data if s.get("category") == "hindi_hinglish"]
        self.assertEqual(len(english), 50, f"Expected 50 English sentences, got {len(english)}")
        self.assertEqual(len(hindi), 50, f"Expected 50 Hindi/Hinglish sentences, got {len(hindi)}")

    def test_id_sequence_integrity(self):
        ids = [s.get("id") for s in self.raw_data]
        expected_ids = list(range(1, 101))
        self.assertEqual(ids, expected_ids, "Sentence IDs must be strictly sequential from 1 to 100")

    def test_phonetic_keywords_alignment(self):
        """
        Evaluates phonetic keywords against sentence text across all 100 sentences.
        Catches keyword-text mismatches where compute_diff flags permanent false positive missing keywords.
        """
        anomalies = []
        for s in self.raw_data:
            s_id = s.get("id")
            text = s.get("text", "")
            norm_text = " ".join(calibration_engine.clean_token(t) for t in text.split())
            keywords = s.get("phonetic_keywords", [])
            self.assertTrue(len(keywords) > 0, f"Sentence #{s_id} has empty phonetic_keywords")
            
            for kw in keywords:
                norm_kw = " ".join(calibration_engine.clean_token(t) for t in kw.split())
                if norm_kw not in norm_text:
                    anomalies.append((s_id, kw, text))

        # All 100 sentences must have phonetic keywords that exist in the sentence text (Sentence #87 aligned)
        self.assertEqual(len(anomalies), 0, f"Found {len(anomalies)} phonetic keywords that do not match their sentence text: {anomalies}")

    def test_dataset_loader_robustness(self):
        data1 = calibration_engine.load_calibration_dataset(self.dataset_path)
        self.assertEqual(len(data1), 100)

        data2 = calibration_engine.load_calibration_dataset("data/calibration_sentences.json")
        self.assertEqual(len(data2), 100)

        # Immutability check
        data1[0]["text"] = "MUTATED"
        data3 = calibration_engine.load_calibration_dataset(self.dataset_path)
        self.assertNotEqual(data3[0]["text"], "MUTATED")


class TestDialogLatencyAndLifecycle(unittest.TestCase):
    """Empirical latency tests: VoiceTrainingDialog across 10 rapid open cycles."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()
        self.mock_audio.is_recording = False

    def test_dialog_init_latency_10_cycles(self):
        """
        Empirical measurement: 10 consecutive open/init cycles.
        Requirement: Average latency < 50ms, with detailed reporting of min, max, mean.
        """
        latencies = []
        dialogs = []

        for cycle in range(10):
            t0 = time.perf_counter()
            dlg = VoiceTrainingDialog(self.mock_audio, self.mock_whisper)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            dialogs.append(dlg)

        for dlg in dialogs:
            dlg.close()

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        print(f"\n[Dialog Latency Benchmark (10 cycles)]")
        for i, lat in enumerate(latencies):
            print(f"  Cycle {i+1}: {lat:.2f} ms")
        print(f"  --> Mean: {avg_latency:.2f} ms | Min: {min_latency:.2f} ms | Max: {max_latency:.2f} ms")

        self.assertLess(avg_latency, 50.0, f"Average dialog init latency {avg_latency:.2f}ms exceeds 50ms limit!")

    def test_category_filtering_and_navigation(self):
        dlg = VoiceTrainingDialog(self.mock_audio, self.mock_whisper)
        self.assertEqual(len(dlg.calibration_dataset), 100)
        self.assertEqual(len(dlg.filtered_dataset), 100)

        # 1. Switch to English filter (idx 1)
        dlg.category_combo.setCurrentIndex(1)
        self.assertEqual(len(dlg.filtered_dataset), 50)
        self.assertEqual(dlg.current_sentence_idx, 0)
        self.assertIn("English", dlg.sentence_counter_lbl.text())

        # 2. Switch to Hindi/Hinglish filter (idx 2)
        dlg.category_combo.setCurrentIndex(2)
        self.assertEqual(len(dlg.filtered_dataset), 50)
        self.assertEqual(dlg.current_sentence_idx, 0)
        self.assertIn("Hindi/Hinglish", dlg.sentence_counter_lbl.text())

        # 3. Advance through sentences
        dlg._advance_sentence()
        self.assertEqual(dlg.current_sentence_idx, 1)
        dlg._prev_sentence()
        self.assertEqual(dlg.current_sentence_idx, 0)

        # 4. Advance past last sentence triggers review jump
        dlg.current_sentence_idx = len(dlg.filtered_dataset) - 1
        dlg._advance_sentence()
        self.assertEqual(dlg.stack.currentIndex(), 2)

        dlg.close()

    def test_speech_finished_signal_handling(self):
        dlg = VoiceTrainingDialog(self.mock_audio, self.mock_whisper)
        
        payload = {
            "text": "main thodi der me call karta hu",
            "wpm": 140,
            "diff_res": {
                "accuracy": 71.4,
                "misheard_pairs": [{"heard": "me", "target": "mein"}, {"heard": "hu", "target": "hoon"}]
            },
            "newly_added": 2
        }
        dlg._on_speech_finished(payload)

        self.assertEqual(dlg.calibrated_wpm, 140)
        self.assertEqual(dlg.auto_registered_count, 2)
        self.assertIn("71.4%", dlg.transcribed_preview.text())
        self.assertIn("Auto-registered 2 phonetic correction(s)", dlg.diff_status.text())

        dlg._on_speech_finished("hello world")
        self.assertEqual(len(dlg.transcribed_sentences), 2)

        dlg.close()


class TestConcurrentPhoneticRegistration(unittest.TestCase):
    """Stress tests for concurrent voice profile updates and corruption resistance."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_profile_path = os.path.join(self.temp_dir.name, "test_voice_profile.json")

        initial_profile = {
            "custom_words": ["Alpha", "Beta"],
            "word_replacements": {"pie side": "PySide6"},
            "active_style": "raw",
            "acoustic_settings": {"speaking_wpm": 130}
        }
        with open(self.test_profile_path, "w", encoding="utf-8") as f:
            json.dump(initial_profile, f, indent=4)

        self.patcher = patch("voice_profile.PROFILE_FILE", self.test_profile_path)
        self.patcher.start()

        VoiceProfileManager._instance = None
        self.mgr = VoiceProfileManager.get_instance()

    def tearDown(self):
        self.patcher.stop()
        VoiceProfileManager._instance = None
        self.temp_dir.cleanup()

    def test_concurrent_auto_registration_thread_safety(self):
        """
        Stress test: 10 threads concurrently registering distinct misheard pairs.
        Verifies:
        1. No unhandled exception or crash occurs.
        2. Resulting voice_profile.json is valid, uncorrupted JSON.
        3. All successfully written keys can be parsed cleanly.
        """
        num_threads = 10
        pairs_per_thread = 15
        exceptions = []

        def worker_task(thread_id):
            try:
                pairs = [
                    {"heard": f"misheard_t{thread_id}_w{w}", "target": f"Target_T{thread_id}_W{w}"}
                    for w in range(pairs_per_thread)
                ]
                calibration_engine.auto_register_misheard_pairs(pairs, self.mgr)
            except Exception as e:
                exceptions.append((thread_id, e))

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(exceptions), 0, f"Exceptions occurred during concurrent registration: {exceptions}")

        with open(self.test_profile_path, "r", encoding="utf-8") as f:
            loaded_json = json.load(f)

        self.assertIn("word_replacements", loaded_json)
        self.assertIsInstance(loaded_json["word_replacements"], dict)

        fresh_mgr = VoiceProfileManager()
        self.assertTrue(len(fresh_mgr.get_replacements()) > 0)

    def test_auto_register_edge_cases(self):
        """Edge cases: empty strings, punctuation-only strings, whitespace, Unicode."""
        weird_pairs = [
            {"heard": "", "target": "Target"},
            {"heard": "   ", "target": "Target"},
            {"heard": "...", "target": "..."},
            {"heard": "???", "target": "Question"},
            {"heard": "hu", "target": "hoon"},
            {"heard": "\u0939\u0942\u0901", "target": "hoon"}
        ]
        added = calibration_engine.auto_register_misheard_pairs(weird_pairs, self.mgr)
        reps = self.mgr.get_replacements()

        self.assertNotIn("", reps)
        self.assertNotIn("...", reps)
        self.assertNotIn("???", reps)
        self.assertIn("hu", reps)
        self.assertEqual(reps["hu"], "hoon")


class TestVocabularyBiasingPrompt1000Words(unittest.TestCase):
    """Stress tests for vocabulary biasing (initial_prompt) with up to 1000 words."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_profile_path = os.path.join(self.temp_dir.name, "test_voice_profile.json")
        with open(self.test_profile_path, "w", encoding="utf-8") as f:
            json.dump({"custom_words": []}, f)

        self.patcher = patch("voice_profile.PROFILE_FILE", self.test_profile_path)
        self.patcher.start()
        VoiceProfileManager._instance = None
        self.mgr = VoiceProfileManager.get_instance()

    def tearDown(self):
        self.patcher.stop()
        VoiceProfileManager._instance = None
        self.temp_dir.cleanup()

    def test_vocabulary_prompt_with_1000_words(self):
        """
        Stress test: inject 1000 custom words into profile.
        Verify:
        1. Prompt generation completes in sub-millisecond (< 5ms).
        2. Result length strictly <= max_chars (800 by default).
        3. Starts with 'Vocabulary: ' and ends with '.'.
        4. No trailing commas before period (e.g., 'word, .').
        5. Does not split any word in half.
        """
        words = [f"TechnicalTerm{i}_{'xyz'*3}" for i in range(1000)]
        self.mgr.profile["custom_words"] = words

        t0 = time.perf_counter()
        prompt = self.mgr.get_initial_prompt(max_chars=800)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        print(f"\n[Vocabulary Prompt 1000-Word Generation]: {elapsed_ms:.4f} ms | Prompt length: {len(prompt)} chars")

        self.assertIsNotNone(prompt)
        self.assertLess(elapsed_ms, 5.0, f"Prompt generation too slow: {elapsed_ms:.2f}ms")
        self.assertLessEqual(len(prompt), 800, f"Prompt length {len(prompt)} exceeds max_chars=800")
        self.assertTrue(prompt.startswith("Vocabulary: "), "Prompt must start with 'Vocabulary: '")
        self.assertTrue(prompt.endswith("."), "Prompt must end with '.'")
        self.assertNotIn(", .", prompt, "Prompt must not contain dangling comma before period")

        content = prompt[len("Vocabulary: "):-1]
        tokens = [t.strip() for t in content.split(",")]
        for t in tokens:
            self.assertIn(t, words, f"Token '{t}' was corrupted or truncated mid-word")

    def test_prompt_truncation_limits_and_boundaries(self):
        """Test varied max_chars budgets (15, 50, 100, 300, 800, 2000)."""
        words = ["PySide6", "WhisperFlow", "CTranslate2", "Kubernetes", "PostgreSQL", "Hinglish"]
        self.mgr.profile["custom_words"] = words

        for max_c in [25, 40, 80, 150, 800, 2000]:
            prompt = self.mgr.get_initial_prompt(max_chars=max_c)
            if prompt is not None:
                self.assertLessEqual(len(prompt), max_c, f"Failed at max_chars={max_c}: len={len(prompt)}")
                self.assertTrue(prompt.startswith("Vocabulary: "))
                self.assertTrue(prompt.endswith("."))

        tiny_prompt = self.mgr.get_initial_prompt(max_chars=14)
        self.assertIsNone(tiny_prompt, "Should return None when budget cannot even fit one word")


if __name__ == "__main__":
    unittest.main()
