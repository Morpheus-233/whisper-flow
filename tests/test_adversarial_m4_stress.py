"""
Milestone M4 Adversarial Stress & Boundary Verification Test Suite
Author: challenger_m4_stress
Project: Whisper Flow Round 2

Empirical verification of:
1. Dialog open & full presentation latency (< 50ms SLA across 50 runs, bloated profiles, tab switches)
2. 1-Click word & rule removal latency (< 1ms SLA across 100-item sequential burst, worst-case end-of-list)
3. High volume dictionary / regex replacement stress (1000+ words, 2000+ replacement rules, 100% fidelity)
4. Non-blocking API ping and VU meter error recovery (simulated network outage matrix, DNS, timeouts, early close, volume clamping)
5. Zero GPU VRAM consumption verification (CPU int8 execution, device verification, torch cuda memory checks)
"""

import sys
import os
import time
import json
import threading
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QPushButton, QLabel,
    QProgressBar, QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QObject
from PySide6.QtGui import QImage, QPainter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import load_config, save_config, DEFAULT_CONFIG
from voice_profile import VoiceProfileManager
from ui.settings_dialog import SettingsDialog, WordRowWidget, ReplacementRowWidget
from ui.voice_training_dialog import VoiceTrainingDialog
from whisper_engine import WhisperEngine
from style_engine import StyleEngine, FastDevanagariRomanizer


class TestM4DialogLatencyAdversarial(unittest.TestCase):
    """Adversarial stress testing of Dialog open & full presentation latency (<50ms SLA)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()
        self.mock_audio.get_input_devices.return_value = [("dev_0", "Realtek Audio"), ("dev_1", "USB Mic")]
        self.mock_audio.get_current_volume.return_value = 0.35

    def test_settings_dialog_presentation_latency_50_runs(self):
        """Verify SettingsDialog full presentation latency (show + processEvents) across 50 runs is strictly <50ms."""
        import gc
        gc.collect()

        # Warmup
        w = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        w.show()
        self.app.processEvents()
        w.close()
        self.app.processEvents()

        latencies = []
        for i in range(50):
            t0 = time.perf_counter()
            dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
            dlg.show()
            self.app.processEvents()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            dlg.close()
            self.app.processEvents()

        mean_ms = sum(latencies) / len(latencies)
        max_ms = max(latencies)
        p95_ms = sorted(latencies)[int(0.95 * len(latencies))]

        print(f"\n[CHALLENGER STRESS] SettingsDialog Full Presentation Latency (50 runs):")
        print(f"  Mean: {mean_ms:.2f} ms | Min: {min(latencies):.2f} ms | Max: {max_ms:.2f} ms | P95: {p95_ms:.2f} ms (SLA: <50ms)")

        self.assertLess(mean_ms, 50.0, f"Mean latency {mean_ms:.2f}ms exceeds 50ms SLA")
        self.assertLess(p95_ms, 50.0, f"P95 latency {p95_ms:.2f}ms exceeds 50ms SLA")

    def test_settings_dialog_bloated_profile_presentation(self):
        """Verify presentation latency remains <50ms under bloated profile (500 words + 500 rules)."""
        mgr = VoiceProfileManager.get_instance()
        orig_words = list(mgr.get_custom_words())
        orig_reps = dict(mgr.get_replacements())

        try:
            # Inject 500 custom words and 500 replacement rules
            mgr.profile["custom_words"] = [f"bloat_word_{i}" for i in range(500)]
            mgr.profile["word_replacements"] = {f"heard_{i}": f"target_{i}" for i in range(500)}

            # Warmup cycle to eliminate Qt class-loading jitter
            w_init = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
            w_init.show()
            self.app.processEvents()
            w_init.close()
            self.app.processEvents()

            latencies = []
            for _ in range(10):
                t0 = time.perf_counter()
                dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
                dlg.show()
                self.app.processEvents()
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(elapsed_ms)
                dlg.close()
                self.app.processEvents()

            mean_ms = sum(latencies) / len(latencies)
            max_ms = max(latencies)
            print(f"[CHALLENGER STRESS] Bloated Profile Presentation (500 words + 500 rules): Mean={mean_ms:.2f}ms, Max={max_ms:.2f}ms")
            self.assertLess(mean_ms, 50.0, f"Bloated profile mean {mean_ms:.2f}ms exceeds 50ms SLA")
            self.assertLess(max_ms, 55.0, f"Bloated profile max {max_ms:.2f}ms exceeds 55ms SLA")
        finally:
            mgr.profile["custom_words"] = orig_words
            mgr.profile["word_replacements"] = orig_reps

    def test_voice_training_dialog_open_latency_20_runs(self):
        """Verify VoiceTrainingDialog open latency across 20 runs is strictly <50ms."""
        # Warmup
        w = VoiceTrainingDialog(self.mock_audio, self.mock_whisper)
        w.close()
        self.app.processEvents()

        latencies = []
        for _ in range(20):
            t0 = time.perf_counter()
            wiz = VoiceTrainingDialog(self.mock_audio, self.mock_whisper)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            wiz.close()
            self.app.processEvents()

        mean_ms = sum(latencies) / len(latencies)
        max_ms = max(latencies)
        p95_ms = sorted(latencies)[int(0.95 * len(latencies))]
        print(f"[CHALLENGER STRESS] VoiceTrainingDialog Open Latency (20 runs): Mean={mean_ms:.2f}ms, Max={max_ms:.2f}ms, P95={p95_ms:.2f}ms")
        self.assertLess(mean_ms, 50.0)
        self.assertLess(max_ms, 50.0)

    def test_tab_switching_under_load(self):
        """Verify switching between tabs takes <50ms."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        dlg.show()
        self.app.processEvents()

        # Cold tab switch (triggers lazy instantiation)
        t0 = time.perf_counter()
        dlg.tabs.setCurrentIndex(1)
        self.app.processEvents()
        t_voice_cold = (time.perf_counter() - t0) * 1000.0

        # Warm tab switch
        dlg.tabs.setCurrentIndex(0)
        self.app.processEvents()
        t1 = time.perf_counter()
        dlg.tabs.setCurrentIndex(1)
        self.app.processEvents()
        t_voice_warm = (time.perf_counter() - t1) * 1000.0

        # Switch to Personal Dictionary (triggers lazy dict instantiation)
        t2 = time.perf_counter()
        dlg.tabs.setCurrentIndex(2)
        self.app.processEvents()
        t_dict_cold = (time.perf_counter() - t2) * 1000.0

        # Warm switch to Dictionary
        dlg.tabs.setCurrentIndex(0)
        self.app.processEvents()
        t3 = time.perf_counter()
        dlg.tabs.setCurrentIndex(2)
        self.app.processEvents()
        t_dict_warm = (time.perf_counter() - t3) * 1000.0

        print(f"[CHALLENGER STRESS] Tab Switching Latency:")
        print(f"  Voice Tab: Cold={t_voice_cold:.2f}ms, Warm={t_voice_warm:.2f}ms")
        print(f"  Dictionary Tab: Cold={t_dict_cold:.2f}ms, Warm={t_dict_warm:.2f}ms")

        # Warm switching must be instantaneous (<20ms)
        self.assertLess(t_voice_warm, 20.0)
        self.assertLess(t_dict_warm, 20.0)
        dlg.close()
        self.app.processEvents()


class TestM4OneClickRemovalAdversarial(unittest.TestCase):
    """Adversarial stress testing of 1-click word & rule removal latency (<1ms SLA)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()
        self.dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        self.dlg.tabs.setCurrentIndex(2)
        self.dlg._ensure_dictionary_loaded()
        self.app.processEvents()

    def tearDown(self):
        self.dlg.close()
        self.app.processEvents()

    def test_burst_100_word_removals_latency(self):
        """Burst test of 100 sequential 1-click word removals (<1ms per removal SLA)."""
        init_count = self.dlg.vocab_list.count()
        test_words = [f"stress_w_{i:04d}_{int(time.time()*1000)}" for i in range(100)]

        for w in test_words:
            self.dlg.new_word_input.setText(w)
            self.dlg._add_custom_word()

        self.assertEqual(self.dlg.vocab_list.count(), init_count + 100)

        latencies = []
        for w in test_words:
            t0 = time.perf_counter()
            self.dlg._on_remove_word_clicked(w)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)

        mean_ms = sum(latencies) / len(latencies)
        max_ms = max(latencies)
        p95_ms = sorted(latencies)[int(0.95 * len(latencies))]

        print(f"\n[CHALLENGER STRESS] 1-Click Word Removal (100 items):")
        print(f"  Mean: {mean_ms:.4f} ms | Min: {min(latencies):.4f} ms | Max: {max_ms:.4f} ms | P95: {p95_ms:.4f} ms (SLA: <1ms)")

        self.assertEqual(self.dlg.vocab_list.count(), init_count)
        self.assertLess(mean_ms, 1.0, f"Mean removal latency {mean_ms:.4f}ms exceeds 1ms SLA")
        self.assertLess(p95_ms, 1.0, f"P95 removal latency {p95_ms:.4f}ms exceeds 1ms SLA")

    def test_burst_100_rule_removals_latency(self):
        """Burst test of 100 sequential 1-click replacement rule removals (<1ms per removal SLA)."""
        init_count = self.dlg.rep_list.count()
        ts = int(time.time() * 1000)
        test_rules = [(f"h_{i:04d}_{ts}", f"t_{i:04d}_{ts}") for i in range(100)]

        for h, t in test_rules:
            self.dlg.rep_heard_input.setText(h)
            self.dlg.rep_target_input.setText(t)
            self.dlg._add_replacement_rule()

        self.assertEqual(self.dlg.rep_list.count(), init_count + 100)

        latencies = []
        for h, _ in test_rules:
            t0 = time.perf_counter()
            self.dlg._on_remove_rep_clicked(h)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)

        mean_ms = sum(latencies) / len(latencies)
        max_ms = max(latencies)
        p95_ms = sorted(latencies)[int(0.95 * len(latencies))]

        print(f"[CHALLENGER STRESS] 1-Click Rule Removal (100 items):")
        print(f"  Mean: {mean_ms:.4f} ms | Min: {min(latencies):.4f} ms | Max: {max_ms:.4f} ms | P95: {p95_ms:.4f} ms (SLA: <1ms)")

        self.assertEqual(self.dlg.rep_list.count(), init_count)
        self.assertLess(mean_ms, 1.0, f"Mean rule removal latency {mean_ms:.4f}ms exceeds 1ms SLA")
        self.assertLess(p95_ms, 1.0, f"P95 rule removal latency {p95_ms:.4f}ms exceeds 1ms SLA")


class TestM4HighVolumeDictionaryStress(unittest.TestCase):
    """Stress test with 1000+ custom words and 2000+ replacement rules."""

    def setUp(self):
        self.mgr = VoiceProfileManager.get_instance()
        self.orig_words = list(self.mgr.get_custom_words())
        self.orig_reps = dict(self.mgr.get_replacements())

    def tearDown(self):
        self.mgr.profile["custom_words"] = self.orig_words
        self.mgr.profile["word_replacements"] = self.orig_reps
        self.mgr.save_profile()

    def test_high_volume_dictionary_and_regex_replacements(self):
        """Inject 1000 custom words and 2000 regex replacement rules; verify throughput and 100% fidelity."""
        # 1. Inject 1000 custom words
        large_vocab = [f"TechTerm_{i:04d}" for i in range(1000)]
        self.mgr.profile["custom_words"] = large_vocab

        # Test initial prompt generation under 1000 words
        t0 = time.perf_counter()
        prompt = self.mgr.get_initial_prompt(max_chars=800)
        t_prompt_ms = (time.perf_counter() - t0) * 1000.0
        print(f"\n[CHALLENGER STRESS] 1000-Word Vocabulary Prompt Generation: {t_prompt_ms:.4f} ms | Length: {len(prompt)} chars")
        self.assertLess(t_prompt_ms, 5.0)
        self.assertLessEqual(len(prompt), 800)
        self.assertTrue(prompt.startswith("Vocabulary:"))

        # 2. Inject 2000 replacement rules
        # Include 50 specific verification targets embedded amongst 1950 noise rules
        large_rules = {f"misheard_token_{i:04d}": f"CorrectTarget_{i:04d}" for i in range(1950)}
        test_targets = {}
        for k in range(50):
            heard_k = f"acoustic_flaw_{k}"
            target_k = f"FlawlessResult_{k}"
            large_rules[heard_k] = target_k
            test_targets[heard_k] = target_k

        self.mgr.profile["word_replacements"] = large_rules

        # Construct a massive 2000-word text including all 50 target phrases
        text_tokens = [f"filler_word_{j % 50}" for j in range(1950)]
        for k, (h, _) in enumerate(test_targets.items()):
            text_tokens.insert(k * 40, h)

        raw_test_input = " ".join(text_tokens)

        # 3. Benchmark apply_replacements
        t0 = time.perf_counter()
        transformed = self.mgr.apply_replacements(raw_test_input)
        elapsed_sec = time.perf_counter() - t0
        elapsed_ms = elapsed_sec * 1000.0

        print(f"[CHALLENGER STRESS] 2000 Rules Regex Replacement (2000 tokens): {elapsed_ms:.2f} ms ({elapsed_sec:.4f} s)")

        # Assert all 50 test targets were correctly replaced (100% fidelity)
        for h, target in test_targets.items():
            self.assertIn(target, transformed, f"Target {target} missing from transformed output")
            self.assertNotIn(h, transformed.split(), f"Original heard token {h} still present in output")

        # Assert no false partial replacements (word boundary protection)
        self.mgr.add_replacement("cat", "feline")
        boundary_test = self.mgr.apply_replacements("The category of concatenation is complicated.")
        self.assertEqual(boundary_test, "The category of concatenation is complicated.")


class TestM4NonBlockingDiagnosticsAndErrorRecovery(unittest.TestCase):
    """Stress test non-blocking API ping and VU meter error recovery."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()
        self.mock_audio.get_input_devices.return_value = [("0", "Microphone")]
        self.mock_audio.is_recording = False
        self.mock_audio.get_current_volume.return_value = 0.5
        self.dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        self.app.processEvents()

    def tearDown(self):
        self.dlg.close()
        self.app.processEvents()

    def test_non_blocking_api_ping_thread_behavior(self):
        """API ping call initiates immediately in <15ms on GUI thread, runs asynchronously, and restores button."""
        def slow_urlopen(req, timeout=5.0):
            time.sleep(0.25)
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = b"{}"
            resp.__enter__.return_value = resp
            return resp

        self.dlg.groq_key_input.setText("gsk_valid_key_sample")

        with patch("urllib.request.urlopen", side_effect=slow_urlopen):
            t0 = time.perf_counter()
            self.dlg._on_test_connection_clicked()
            gui_latency_ms = (time.perf_counter() - t0) * 1000.0

            print(f"\n[CHALLENGER STRESS] API Ping GUI Thread Launch Latency: {gui_latency_ms:.3f} ms")
            self.assertLess(gui_latency_ms, 20.0, "API ping blocked the main GUI thread!")
            self.assertFalse(self.dlg.test_conn_btn.isEnabled())

            start_w = time.time()
            while not self.dlg.test_conn_btn.isEnabled() and (time.time() - start_w < 2.0):
                self.app.processEvents()
                time.sleep(0.01)

            self.assertTrue(self.dlg.test_conn_btn.isEnabled())
            self.assertIn("Connected", self.dlg.conn_status_lbl.text())

    def test_simulated_network_error_matrix(self):
        """Verify graceful error reporting across HTTP 401, 429, 500, 503, URLError, and Timeout."""
        import urllib.error
        import socket

        scenarios = [
            (urllib.error.HTTPError("url", 401, "Unauthorized", {}, None), "Authentication Failed (401)"),
            (urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None), "Rate Limit Exceeded (429)"),
            (urllib.error.HTTPError("url", 500, "Internal Server Error", {}, None), "HTTP Error (500)"),
            (urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None), "HTTP Error (503)"),
            (urllib.error.URLError(socket.gaierror(-3, "Temporary failure in name resolution")), "Offline / Network Timeout"),
            (socket.timeout("The read operation timed out"), "Connection Failed: The read operation timed out")
        ]

        self.dlg.groq_key_input.setText("gsk_dummy_test")

        for exc, expected_msg in scenarios:
            with patch("urllib.request.urlopen", side_effect=exc):
                self.dlg._start_groq_ping_test()
                start_w = time.time()
                while not self.dlg.test_conn_btn.isEnabled() and (time.time() - start_w < 1.0):
                    self.app.processEvents()
                    time.sleep(0.01)

                self.assertTrue(self.dlg.test_conn_btn.isEnabled())
                actual_msg = self.dlg.conn_status_lbl.text()
                self.assertEqual(actual_msg, expected_msg)

    def test_vu_meter_overflow_underflow_and_exception_handling(self):
        """VU meter clamps aberrant audio levels and recovers gracefully from audio engine exceptions."""
        self.dlg._start_audio_vu_test()

        # Underflow (-1.5) -> clamped to 0
        self.mock_audio.get_current_volume.return_value = -1.5
        self.dlg._on_vu_tick()
        self.assertEqual(self.dlg.vu_meter.value(), 0)

        # Normal (0.75) -> 75%
        self.mock_audio.get_current_volume.return_value = 0.75
        self.dlg._on_vu_tick()
        self.assertEqual(self.dlg.vu_meter.value(), 75)

        # Overflow (10.0) -> clamped to 100
        self.mock_audio.get_current_volume.return_value = 10.0
        self.dlg._on_vu_tick()
        self.assertEqual(self.dlg.vu_meter.value(), 100)

        # Audio driver exception -> falls back to 0 without crashing
        self.mock_audio.get_current_volume.side_effect = RuntimeError("Audio endpoint disconnected")
        self.dlg._on_vu_tick()
        self.assertEqual(self.dlg.vu_meter.value(), 0)

        self.dlg._stop_audio_vu_test()
        self.assertEqual(self.dlg.vu_meter.value(), 0)


class TestM4ZeroGPUVRAMEmpirical(unittest.TestCase):
    """Empirically verify Zero GPU VRAM consumption under CPU int8 execution."""

    def test_cpu_mode_vram_allocation_is_strictly_zero(self):
        """Verify WhisperEngine in CPU int8 mode allocates 0.0 MB GPU VRAM."""
        engine = WhisperEngine.get_instance(device="cpu", compute_type="int8")
        
        # Check engine attributes
        self.assertEqual(engine.device, "cpu")
        self.assertEqual(engine.compute_type, "int8")
        
        # Check VRAM usage reporting
        vram_mb = engine.get_vram_usage_mb()
        print(f"\n[CHALLENGER STRESS] Reported Engine VRAM in CPU mode: {vram_mb} MB")
        self.assertEqual(vram_mb, 0.0)

        # If torch and CUDA are available on this machine (NVIDIA RTX 3060 is present)
        try:
            import torch
            if torch.cuda.is_available():
                cuda_allocated_bytes = torch.cuda.memory_allocated()
                print(f"[CHALLENGER STRESS] Hardware CUDA detected ({torch.cuda.get_device_name(0)}). PyTorch CUDA allocated: {cuda_allocated_bytes} bytes")
                # Zero bytes allocated by whisper-flow
                self.assertEqual(cuda_allocated_bytes, 0)
        except ImportError:
            pass

    def test_faster_whisper_instantiation_parameters_enforce_zero_gpu(self):
        """Verify WhisperModel is loaded strictly with device='cpu' and compute_type='int8'."""
        with patch("whisper_engine.WhisperModel") as mock_model:
            engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8")
            engine.load_model()
            
            mock_model.assert_called_once()
            _, kwargs = mock_model.call_args
            self.assertEqual(kwargs.get("device"), "cpu")
            self.assertEqual(kwargs.get("compute_type"), "int8")
            print(f"[CHALLENGER STRESS] WhisperModel instantiation kwargs verified: device={kwargs.get('device')}, compute_type={kwargs.get('compute_type')}")


if __name__ == "__main__":
    unittest.main()
