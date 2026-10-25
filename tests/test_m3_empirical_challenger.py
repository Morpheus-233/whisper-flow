"""
Empirical Adversarial Stress Test Suite for Milestone M3
Whisper Flow Round 2 — Unified Settings UI & Floating Capsule Badges

Adversarially tests:
1. SettingsDialog presentation latency (<50ms across 50 sequential runs, cold/warm, bloated profiles)
2. 1-Click word and replacement rule removal (<1ms under 50-item sequential burst, worst-case end-of-list, edge cases)
3. Concurrent signals and status badge updates on 148x34px dock (multi-threaded bursts, bounds, state transitions)
4. Non-blocking API ping & VU meter error resilience (network timeouts, HTTP 401/429/500/503, DNS failures, dialog close in-flight, abnormal audio levels)
"""

import sys
import os
import time
import math
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
from ui.floating_widget import FloatingWidget, STATE_IDLE, STATE_RECORDING, STATE_PASTED, STATE_TRANSCRIBING


class TestSettingsDialogLatencyEmpirical(unittest.TestCase):
    """Adversarial stress testing of SettingsDialog presentation latency."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()
        self.mock_audio.get_input_devices.return_value = [("dev_0", "Realtek Audio"), ("dev_1", "USB Mic")]
        self.mock_audio.get_current_volume.return_value = 0.35

    def test_settings_dialog_constructor_latency_50_runs(self):
        """Measures pure instantiation latency across 50 runs."""
        latencies = []
        for _ in range(50):
            t0 = time.perf_counter()
            dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)
            dlg.close()

        mean_ms = sum(latencies) / len(latencies)
        max_ms = max(latencies)
        print(f"\n[M3 STRESS] SettingsDialog Constructor Latency (50 runs): Mean={mean_ms:.2f}ms, Max={max_ms:.2f}ms")
        self.assertLess(mean_ms, 50.0)

    def test_settings_dialog_full_presentation_latency_50_runs(self):
        """Stress test full SettingsDialog presentation (show + processEvents) across 50 sequential runs (<50ms SLA)."""
        import gc
        gc.collect()

        # Warmup pass to eliminate one-off OS/Qt surface creation jitter
        warmup = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        warmup.show()
        self.app.processEvents()
        warmup.close()
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
        min_ms = min(latencies)
        p95_ms = sorted(latencies)[int(0.95 * len(latencies))]

        print(f"\n[M3 STRESS] SettingsDialog Full Presentation Latency (50 runs with show + processEvents):")
        print(f"  Mean: {mean_ms:.2f} ms | Min: {min_ms:.2f} ms | Max: {max_ms:.2f} ms | P95: {p95_ms:.2f} ms")

        # Record empirical result: this will fail if singleShot(0, _ensure_dictionary_loaded) causes >50ms latency
        self.assertLess(mean_ms, 50.0, f"Full presentation mean latency {mean_ms:.2f}ms exceeds 50ms SLA")
        self.assertLess(p95_ms, 55.0, f"Full presentation p95 latency {p95_ms:.2f}ms exceeds 55ms SLA")

    def test_settings_dialog_bloated_profile_presentation(self):
        """SettingsDialog presentation under bloated profile (150 words + 150 rules)."""
        mgr = VoiceProfileManager.get_instance()
        orig_words = list(mgr.get_custom_words())
        orig_reps = dict(mgr.get_replacements())

        try:
            # Inject 150 custom words and 150 rules
            mgr.profile["custom_words"] = [f"bloat_word_{i}" for i in range(150)]
            mgr.profile["word_replacements"] = {f"heard_{i}": f"target_{i}" for i in range(150)}

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
            print(f"[M3 STRESS] Bloated Profile Presentation (150 words + 150 rules): Mean={mean_ms:.2f}ms, Max={max_ms:.2f}ms")
            self.assertLess(mean_ms, 50.0, f"Bloated profile presentation mean {mean_ms:.2f}ms exceeds 50ms SLA")
        finally:
            mgr.profile["custom_words"] = orig_words
            mgr.profile["word_replacements"] = orig_reps

    def test_tab_switching_under_load(self):
        """Switching to Voice tab and Dictionary tab must complete smoothly under 50ms."""
        dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        dlg.show()
        self.app.processEvents()

        t0 = time.perf_counter()
        dlg.tabs.setCurrentIndex(1)
        self.app.processEvents()
        t_voice = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        dlg.tabs.setCurrentIndex(2)
        self.app.processEvents()
        t_dict = (time.perf_counter() - t1) * 1000.0

        print(f"[M3 STRESS] Tab Switching Latency: Voice Tab={t_voice:.2f}ms, Dictionary Tab={t_dict:.2f}ms")
        self.assertLess(t_voice, 50.0)
        self.assertLess(t_dict, 50.0)
        dlg.close()
        self.app.processEvents()


class TestOneClickRemovalEmpirical(unittest.TestCase):
    """Adversarial stress testing of 1-click word and replacement rule removal (<1ms)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.mock_whisper = MagicMock()
        self.mock_audio.get_input_devices.return_value = [("0", "Microphone")]
        self.dlg = SettingsDialog(self.cfg, self.mock_audio, self.mock_whisper)
        self.dlg.tabs.setCurrentIndex(2)
        self.dlg._ensure_dictionary_loaded()
        self.app.processEvents()

    def tearDown(self):
        self.dlg.close()
        self.app.processEvents()

    def test_sequential_50_word_removals_latency(self):
        """Stress test 50 sequential 1-click word removals (<1ms per removal)."""
        init_count = self.dlg.vocab_list.count()
        test_words = [f"stress_w_{i:03d}_{int(time.time()*1000)}" for i in range(50)]

        # Pre-populate
        for w in test_words:
            self.dlg.new_word_input.setText(w)
            self.dlg._add_custom_word()

        self.assertEqual(self.dlg.vocab_list.count(), init_count + 50)

        removal_latencies = []
        for w in test_words:
            t0 = time.perf_counter()
            self.dlg._on_remove_word_clicked(w)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            removal_latencies.append(elapsed_ms)

        mean_ms = sum(removal_latencies) / len(removal_latencies)
        max_ms = max(removal_latencies)
        p95_ms = sorted(removal_latencies)[int(0.95 * len(removal_latencies))]

        print(f"\n[M3 STRESS] 1-Click Word Removal Latency (50 items):")
        print(f"  Mean: {mean_ms:.4f} ms | Min: {min(removal_latencies):.4f} ms | Max: {max_ms:.4f} ms | P95: {p95_ms:.4f} ms")

        self.assertEqual(self.dlg.vocab_list.count(), init_count)
        self.assertLess(mean_ms, 1.0, f"Mean removal latency {mean_ms:.4f}ms exceeds 1ms SLA")
        self.assertLess(max_ms, 2.0, f"Max removal latency {max_ms:.4f}ms exceeds burst limit")

    def test_sequential_50_replacement_rule_removals_latency(self):
        """Stress test 50 sequential 1-click replacement rule removals (<1ms per removal)."""
        init_count = self.dlg.rep_list.count()
        ts = int(time.time() * 1000)
        test_rules = [(f"h_{i:03d}_{ts}", f"t_{i:03d}_{ts}") for i in range(50)]

        # Pre-populate
        for h, t in test_rules:
            self.dlg.rep_heard_input.setText(h)
            self.dlg.rep_target_input.setText(t)
            self.dlg._add_replacement_rule()

        self.assertEqual(self.dlg.rep_list.count(), init_count + 50)

        removal_latencies = []
        for h, _ in test_rules:
            t0 = time.perf_counter()
            self.dlg._on_remove_rep_clicked(h)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            removal_latencies.append(elapsed_ms)

        mean_ms = sum(removal_latencies) / len(removal_latencies)
        max_ms = max(removal_latencies)
        p95_ms = sorted(removal_latencies)[int(0.95 * len(removal_latencies))]

        print(f"[M3 STRESS] 1-Click Replacement Rule Removal Latency (50 items):")
        print(f"  Mean: {mean_ms:.4f} ms | Min: {min(removal_latencies):.4f} ms | Max: {max_ms:.4f} ms | P95: {p95_ms:.4f} ms")

        self.assertEqual(self.dlg.rep_list.count(), init_count)
        self.assertLess(mean_ms, 1.0, f"Mean rule removal latency {mean_ms:.4f}ms exceeds 1ms SLA")
        self.assertLess(max_ms, 2.0, f"Max rule removal latency {max_ms:.4f}ms exceeds burst limit")

    def test_removal_edge_cases_and_filter_resilience(self):
        """Adversarial removal edge cases: non-existent item, empty list, active filter, special chars."""
        # 1. Non-existent word removal from list
        self.dlg._on_remove_word_clicked("ghost_word_that_does_not_exist")  # Should not raise

        # 2. Add special chars, Devanagari, and spaces
        ts = int(time.time() * 1000)
        special_words = [f"नमस्ते_{ts}", f"alpha-beta_{ts}", f"hello world_{ts}", f"C++ / Rust_{ts}"]
        for w in special_words:
            self.dlg.new_word_input.setText(w)
            self.dlg._add_custom_word()

        # 3. Apply active filter
        self.dlg.vocab_filter_input.setText("alpha")
        self.app.processEvents()

        # 4. Remove a hidden item directly
        t0 = time.perf_counter()
        self.dlg._on_remove_word_clicked(f"नमस्ते_{ts}")
        t_del = (time.perf_counter() - t0) * 1000.0
        self.assertLess(t_del, 1.0)

        # 5. Remove visible item
        t0 = time.perf_counter()
        self.dlg._on_remove_word_clicked(f"alpha-beta_{ts}")
        t_del2 = (time.perf_counter() - t0) * 1000.0
        self.assertLess(t_del2, 1.0)

        # Clean remaining
        for w in special_words:
            self.dlg._on_remove_word_clicked(w)


class TestCapsuleDockGeometryAndConcurrentSignals(unittest.TestCase):
    """Stress test FloatingWidget 148x34px dock geometry and concurrent signals."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.cfg = load_config()
        self.mock_audio = MagicMock()
        self.mock_audio.get_current_volume.return_value = 0.4
        self.widget = FloatingWidget(self.cfg, self.mock_audio)

    def tearDown(self):
        self.widget.close()
        self.app.processEvents()

    def test_dock_geometry_invariants(self):
        """FloatingWidget idle geometry invariants: dock_w=64, dock_h=34, pad_x=7, pad_y=6."""
        self.widget.set_state(STATE_IDLE)
        self.app.processEvents()

        self.assertEqual(self.widget.dock_w, 64)
        self.assertEqual(self.widget.dock_h, 34)
        expected_w = 64 + self.widget.pad_x * 2  # 78
        expected_h = 34 + self.widget.pad_y * 2   # 46
        self.assertEqual(self.widget.width(), expected_w)
        self.assertEqual(self.widget.height(), expected_h)

    def test_rapid_state_transitions_preserve_center(self):
        """Rapid state transitions between idle dock and recording bar maintain center anchor."""
        self.widget.move(500, 500)
        orig_center_x = self.widget.x() + self.widget.width() // 2
        orig_center_y = self.widget.y() + self.widget.height() // 2

        for _ in range(20):
            self.widget.set_state(STATE_RECORDING)
            self.app.processEvents()
            cur_center_x = self.widget.x() + self.widget.width() // 2
            cur_center_y = self.widget.y() + self.widget.height() // 2
            self.assertEqual(orig_center_x, cur_center_x)
            self.assertEqual(orig_center_y, cur_center_y)

            self.widget.set_state(STATE_IDLE)
            self.app.processEvents()
            cur_center_x2 = self.widget.x() + self.widget.width() // 2
            cur_center_y2 = self.widget.y() + self.widget.height() // 2
            self.assertEqual(orig_center_x, cur_center_x2)
            self.assertEqual(orig_center_y, cur_center_y2)

    def test_concurrent_signal_bursts_on_status_badges(self):
        """Concurrent burst of 150 status badge updates across threads."""
        errors = []

        def worker_thread(engine_val, lang_val):
            try:
                for _ in range(50):
                    self.widget.update_status_badges(engine_val, lang_val)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=worker_thread, args=("groq", "hinglish"))
        t2 = threading.Thread(target=worker_thread, args=("local", "english"))
        t3 = threading.Thread(target=worker_thread, args=("groq", "hi-en"))

        t1.start()
        t2.start()
        t3.start()

        while t1.is_alive() or t2.is_alive() or t3.is_alive():
            self.app.processEvents()
            time.sleep(0.005)

        t1.join()
        t2.join()
        t3.join()

        self.assertEqual(len(errors), 0, f"Thread errors encountered: {errors}")
        self.assertIn(self.widget.active_engine, ("groq", "local"))

    def test_paint_event_stress_matrix(self):
        """Render paintEvent across all edge combinations onto offscreen QImage."""
        combos = [
            ("groq", "hinglish"),
            ("local", "english"),
            ("local", "hinglish"),
            ("groq", "en"),
            ("groq", "hi-en"),
            ("", ""),
            ("unknown_engine", "unknown_lang"),
            (None, None),
        ]

        img = QImage(self.widget.width(), self.widget.height(), QImage.Format.Format_ARGB32_Premultiplied)
        for eng, lng in combos:
            self.widget.active_engine = eng
            self.widget.active_language = lng
            painter = QPainter(img)
            try:
                self.widget.paintEvent(MagicMock())
            finally:
                painter.end()


class TestNonBlockingApiPingAndVuMeterResilience(unittest.TestCase):
    """Stress test non-blocking API ping and VU meter under simulated network & audio errors."""

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

    def test_api_ping_non_blocking_during_slow_network(self):
        """API ping runs asynchronously on daemon thread; GUI does not freeze under delay."""
        def slow_urlopen(req, timeout=5.0):
            time.sleep(0.3)
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = b"{}"
            resp.__enter__.return_value = resp
            return resp

        self.dlg.groq_key_input.setText("gsk_test_key_12345")

        with patch("urllib.request.urlopen", side_effect=slow_urlopen):
            t0 = time.perf_counter()
            self.dlg._on_test_connection_clicked()
            elapsed_gui_call = (time.perf_counter() - t0) * 1000.0

            self.assertLess(elapsed_gui_call, 20.0)
            self.assertEqual(self.dlg.conn_status_lbl.text(), "Testing connection...")
            self.assertFalse(self.dlg.test_conn_btn.isEnabled())

            start_wait = time.time()
            while not self.dlg.test_conn_btn.isEnabled() and (time.time() - start_wait < 2.0):
                self.app.processEvents()
                time.sleep(0.01)

            self.assertTrue(self.dlg.test_conn_btn.isEnabled())
            self.assertIn("Connected", self.dlg.conn_status_lbl.text())

    def test_api_ping_simulated_network_error_matrix(self):
        """Verify clean error messaging across HTTP 401, 429, 500, 503, URLError, Timeout."""
        import urllib.error
        import socket

        error_scenarios = [
            (urllib.error.HTTPError("url", 401, "Unauthorized", {}, None), "Authentication Failed (401)"),
            (urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None), "Rate Limit Exceeded (429)"),
            (urllib.error.HTTPError("url", 500, "Internal Server Error", {}, None), "HTTP Error (500)"),
            (urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None), "HTTP Error (503)"),
            (urllib.error.URLError(socket.gaierror(-3, "Temporary failure in name resolution")), "Offline / Network Timeout"),
            (socket.timeout("The read operation timed out"), "Connection Failed: The read operation timed out"),
        ]

        self.dlg.groq_key_input.setText("gsk_dummy_key")

        for exc, expected_text in error_scenarios:
            with patch("urllib.request.urlopen", side_effect=exc):
                self.dlg._start_groq_ping_test()
                start_w = time.time()
                while not self.dlg.test_conn_btn.isEnabled() and (time.time() - start_w < 1.0):
                    self.app.processEvents()
                    time.sleep(0.01)

                self.assertTrue(self.dlg.test_conn_btn.isEnabled())
                actual_text = self.dlg.conn_status_lbl.text()
                self.assertEqual(actual_text, expected_text, f"Expected '{expected_text}', got '{actual_text}'")

    def test_api_ping_thread_resilience_when_dialog_closed_early(self):
        """Dialog rejected/closed while background ping thread in flight must not crash."""
        def delayed_urlopen(req, timeout=5.0):
            time.sleep(0.2)
            resp = MagicMock()
            resp.status = 200
            resp.read.return_value = b"{}"
            resp.__enter__.return_value = resp
            return resp

        self.dlg.groq_key_input.setText("gsk_test_key")
        with patch("urllib.request.urlopen", side_effect=delayed_urlopen):
            self.dlg._start_groq_ping_test()
            self.dlg.reject()
            self.app.processEvents()

            time.sleep(0.3)
            self.app.processEvents()

    def test_vu_meter_audio_clamping_and_exceptions(self):
        """VU meter handles abnormal volume levels [0, 100] and audio engine exceptions."""
        self.dlg._start_audio_vu_test()

        # 1. Normal level 0.5 -> 50%
        self.mock_audio.get_current_volume.return_value = 0.50
        self.dlg._on_vu_tick()
        self.assertEqual(self.dlg.vu_meter.value(), 50)

        # 2. Level 0.0 -> 0%
        self.mock_audio.get_current_volume.return_value = 0.0
        self.dlg._on_vu_tick()
        self.assertEqual(self.dlg.vu_meter.value(), 0)

        # 3. Level 1.0 -> 100%
        self.mock_audio.get_current_volume.return_value = 1.0
        self.dlg._on_vu_tick()
        self.assertEqual(self.dlg.vu_meter.value(), 100)

        # 4. Overflow level 3.5 -> clamped to 100%
        self.mock_audio.get_current_volume.return_value = 3.5
        self.dlg._on_vu_tick()
        self.assertEqual(self.dlg.vu_meter.value(), 100)

        # 5. Underflow level -1.2 -> clamped to 0%
        self.mock_audio.get_current_volume.return_value = -1.2
        self.dlg._on_vu_tick()
        self.assertEqual(self.dlg.vu_meter.value(), 0)

        # 6. AudioEngine raises exception -> catches and sets 0
        self.mock_audio.get_current_volume.side_effect = RuntimeError("Audio device disconnected")
        self.dlg._on_vu_tick()
        self.assertEqual(self.dlg.vu_meter.value(), 0)

        # 7. Stop audio test -> resets to 0 and stops timer
        self.dlg._stop_audio_vu_test()
        self.assertEqual(self.dlg.vu_meter.value(), 0)
        self.assertFalse(self.dlg._vu_timer.isActive())


if __name__ == "__main__":
    unittest.main()
