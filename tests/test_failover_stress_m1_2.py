"""
Empirical Adversarial Stress Test Suite: Challenger M1-2.
Whisper Flow Round 2 — Milestone 1 Specification.

Verifies:
1. Simulated Groq network failures:
   - HTTP 401 Unauthorized
   - HTTP 429 Rate Limit Exceeded
   - HTTP 503 Service Outage
   - Socket Timeout
   - DNS / Connection Refused (URLError)
   - Malformed / HTML payload
   - Transparent failover to local CPU int8 without application hang or crash
2. 100% Offline execution with engine_mode == "local":
   - Zero network requests
   - Zero MB GPU VRAM allocation (verified on physical RTX 3060 if available)
   - device="cpu", compute_type="int8"
3. Developer Mode casing transformations and operator conversions on complex Hinglish developer phrases:
   - camelCase, snake_case, kebab-case, PascalCase, CONSTANT_CASE
   - All programming operators (=>, ->, ===, !==, ==, !=, >=, <=, +=, -=, *=, /=, :=, ++, --, &&, ||, ??, ?.)
   - Delimiters, files (.env, .gitignore, etc.), console.log, try/catch, async/await
   - Complex compound Hinglish phrases & Devanagari acoustic input
4. Concurrency Stress:
   - Multi-threaded concurrent execution under active network failures
"""

import sys
import os
import io
import time
import socket
import json
import threading
import unittest
from unittest.mock import MagicMock, patch
import urllib.request
import urllib.error

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from whisper_engine import WhisperEngine
from style_engine import StyleEngine, FastDevanagariRomanizer
from text_cleaner import format_developer_mode, format_casual_chat, format_custom_persona
from voice_profile import VoiceProfileManager


def make_mock_http_error(code: int, message: str, body_dict: dict = None) -> urllib.error.HTTPError:
    """Helper to construct realistic urllib.error.HTTPError instances."""
    if body_dict is None:
        body_dict = {"error": {"message": message, "code": code}}
    raw_bytes = json.dumps(body_dict).encode("utf-8")
    fp = io.BytesIO(raw_bytes)
    return urllib.error.HTTPError(
        url="https://api.groq.com/openai/v1/audio/transcriptions",
        code=code,
        msg=message,
        hdrs={},
        fp=fp
    )


class TestGroqFailoverAcousticCapture(unittest.TestCase):
    """
    Empirically verifies Stage 1 acoustic capture Groq network failures
    and automatic seamless failover to local CPU int8 model.
    """

    def setUp(self):
        # Fresh isolated engine instance
        self.engine = WhisperEngine(
            model_name="base",
            device="cpu",
            compute_type="int8",
            groq_api_key="gsk_empirical_test_key",
            engine_mode="groq"
        )
        self.mock_local_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Local fallback Hinglish transcription successful"
        self.mock_local_model.transcribe.return_value = ([mock_segment], MagicMock())
        self.engine.model = self.mock_local_model

        self.audio_data = np.ones(16000, dtype=np.float32) * 0.1

    @patch("whisper_engine.urllib.request.urlopen")
    def test_groq_http_401_unauthorized_failover(self, mock_urlopen):
        """HTTP 401 Unauthorized must log, failover to local CPU int8, and never crash."""
        mock_urlopen.side_effect = make_mock_http_error(401, "Invalid API Key")

        t0 = time.perf_counter()
        result = self.engine.transcribe_stage1(self.audio_data)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(result, "Local fallback Hinglish transcription successful")
        self.mock_local_model.transcribe.assert_called_once()
        self.assertLess(elapsed_ms, 500.0, f"Failover too slow: {elapsed_ms:.2f}ms")

    @patch("whisper_engine.urllib.request.urlopen")
    def test_groq_http_429_rate_limit_failover(self, mock_urlopen):
        """HTTP 429 Rate Limit Exceeded must failover to local CPU int8 immediately."""
        mock_urlopen.side_effect = make_mock_http_error(429, "Rate limit reached for model")

        t0 = time.perf_counter()
        result = self.engine.transcribe_stage1(self.audio_data)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(result, "Local fallback Hinglish transcription successful")
        self.mock_local_model.transcribe.assert_called_once()
        self.assertLess(elapsed_ms, 500.0, f"Failover too slow: {elapsed_ms:.2f}ms")

    @patch("whisper_engine.urllib.request.urlopen")
    def test_groq_http_503_service_outage_failover(self, mock_urlopen):
        """HTTP 503 Service Outage must failover to local CPU int8 immediately."""
        mock_urlopen.side_effect = make_mock_http_error(503, "Groq Cloud Service Unavailable")

        t0 = time.perf_counter()
        result = self.engine.transcribe_stage1(self.audio_data)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(result, "Local fallback Hinglish transcription successful")
        self.mock_local_model.transcribe.assert_called_once()
        self.assertLess(elapsed_ms, 500.0, f"Failover too slow: {elapsed_ms:.2f}ms")

    @patch("whisper_engine.urllib.request.urlopen")
    def test_groq_socket_timeout_failover(self, mock_urlopen):
        """Socket timeout during audio upload must trigger local CPU failover without hanging."""
        mock_urlopen.side_effect = urllib.error.URLError(socket.timeout("The read operation timed out"))

        t0 = time.perf_counter()
        result = self.engine.transcribe_stage1(self.audio_data)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertEqual(result, "Local fallback Hinglish transcription successful")
        self.mock_local_model.transcribe.assert_called_once()
        self.assertLess(elapsed_ms, 500.0, f"Failover took too long: {elapsed_ms:.2f}ms")

    @patch("whisper_engine.urllib.request.urlopen")
    def test_groq_dns_failure_urlerror_failover(self, mock_urlopen):
        """DNS resolution failure (offline device) must failover seamlessly."""
        mock_urlopen.side_effect = urllib.error.URLError("[Errno 11001] getaddrinfo failed")

        result = self.engine.transcribe_stage1(self.audio_data)
        self.assertEqual(result, "Local fallback Hinglish transcription successful")
        self.mock_local_model.transcribe.assert_called_once()

    @patch("whisper_engine.urllib.request.urlopen")
    def test_groq_malformed_html_error_payload_failover(self, mock_urlopen):
        """When an intermediary proxy returns 200/502 with HTML content, engine must not crash on JSON decode."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.code = 200
        mock_resp.read.return_value = b"<!DOCTYPE html><html><body>502 Bad Gateway</body></html>"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = self.engine.transcribe_stage1(self.audio_data)
        self.assertEqual(result, "Local fallback Hinglish transcription successful")
        self.mock_local_model.transcribe.assert_called_once()

    @patch("whisper_engine.urllib.request.urlopen")
    def test_groq_explicit_error_json_failover(self, mock_urlopen):
        """When Groq returns JSON containing an 'error' dictionary field, engine must failover."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.code = 200
        mock_resp.read.return_value = json.dumps({"error": {"message": "GPU worker crash", "type": "server_error"}}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = self.engine.transcribe_stage1(self.audio_data)
        self.assertEqual(result, "Local fallback Hinglish transcription successful")
        self.mock_local_model.transcribe.assert_called_once()


class TestGroqFailoverStage2Romanizer(unittest.TestCase):
    """
    Empirically verifies Stage 2 Groq LLM Romanizer failures,
    circuit breaker operation, and fallback to local CPU Romanizer/Stylist.
    """

    def setUp(self):
        StyleEngine._unauthorized_keys.clear()

    @patch("style_engine.urllib.request.urlopen")
    def test_stage2_http_401_circuit_breaker(self, mock_urlopen):
        """
        HTTP 401 on Stage 2 must register the key into _unauthorized_keys circuit breaker,
        fall back to local CPU Romanizer, and bypass all future network attempts.
        """
        mock_urlopen.side_effect = make_mock_http_error(401, "Invalid API Key")
        test_key = "gsk_invalid_test_key_401"

        raw_hindi = "मैं कल कोड पुश कर दूंगा।"

        # First invocation hits network and gets 401
        res1 = StyleEngine.format_two_stage(raw_hindi, style="casual", groq_api_key=test_key, engine_mode="groq")
        self.assertTrue(
            "main kal code push kar dunga" in res1.lower() or "main kal code push kar doonga" in res1.lower(),
            f"Expected Romanized Hinglish push kar dunga/doonga, got: {res1}"
        )
        self.assertIn(test_key, StyleEngine._unauthorized_keys)
        self.assertEqual(mock_urlopen.call_count, 1)

        # Second invocation: Circuit breaker must intercept BEFORE urlopen
        t0 = time.perf_counter()
        res2 = StyleEngine.format_two_stage(raw_hindi, style="casual", groq_api_key=test_key, engine_mode="groq")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertTrue(
            "main kal code push kar dunga" in res2.lower() or "main kal code push kar doonga" in res2.lower(),
            f"Expected Romanized Hinglish push kar dunga/doonga, got: {res2}"
        )
        self.assertEqual(mock_urlopen.call_count, 1, "Circuit breaker failed to block network request!")
        self.assertLess(elapsed_ms, 5.0, f"Circuit breaker should be instant (<5ms), took {elapsed_ms:.2f}ms")

    @patch("style_engine.urllib.request.urlopen")
    def test_stage2_http_429_rate_limit_fallback(self, mock_urlopen):
        """HTTP 429 on Stage 2 falls back cleanly to local Romanizer & style processor."""
        mock_urlopen.side_effect = make_mock_http_error(429, "Rate limit reached")

        raw_text = "स्टेजिंग सर्वर पर डिप्लॉय हो गया है pakka."
        res = StyleEngine.format_two_stage(raw_text, style="casual", groq_api_key="gsk_valid_key", engine_mode="groq")

        self.assertFalse(FastDevanagariRomanizer.has_devanagari(res))
        self.assertIn("staging server par deploy ho gaya hai", res.lower())
        self.assertFalse(res.endswith("."))

    @patch("style_engine.urllib.request.urlopen")
    def test_stage2_http_503_outage_fallback(self, mock_urlopen):
        """HTTP 503 on Stage 2 falls back cleanly to local Romanizer & style processor."""
        mock_urlopen.side_effect = make_mock_http_error(503, "Service Unavailable")

        raw_text = "camel case user profile id bana do"
        res = StyleEngine.format_two_stage(raw_text, style="developer", groq_api_key="gsk_valid_key", engine_mode="groq")

        self.assertIn("userProfileId", res)

    @patch("style_engine.urllib.request.urlopen")
    def test_stage2_socket_timeout_fallback(self, mock_urlopen):
        """Socket timeout on Stage 2 falls back cleanly to local Romanizer & style processor."""
        mock_urlopen.side_effect = urllib.error.URLError(socket.timeout("Timed out"))

        raw_text = "Main kal code push kar dunga pakka."
        res = StyleEngine.format_two_stage(raw_text, style="casual", groq_api_key="gsk_valid_key", engine_mode="groq")

        self.assertIn("main kal code push kar dunga", res.lower())


class TestConcurrentFailoverUnderNetworkFailure(unittest.TestCase):
    """
    Stress-tests multi-threaded concurrent calls to WhisperEngine.transcribe
    while Groq Cloud is experiencing simultaneous network failures.
    """

    def setUp(self):
        self.engine = WhisperEngine(
            model_name="base",
            device="cpu",
            compute_type="int8",
            groq_api_key="gsk_concurrent_key",
            engine_mode="groq"
        )
        self.mock_local = MagicMock()
        mock_seg = MagicMock()
        mock_seg.text = "Concurrent local Hinglish output"
        self.mock_local.transcribe.return_value = ([mock_seg], MagicMock())
        self.engine.model = self.mock_local

    @patch("whisper_engine.urllib.request.urlopen")
    @patch("style_engine.urllib.request.urlopen")
    def test_concurrent_transcriptions_during_groq_outage(self, mock_style_url, mock_whisper_url):
        """
        10 threads simultaneously calling transcribe() during total Groq 503 outage.
        Verifies:
        1. Zero exceptions raised across any thread.
        2. All 10 threads return valid transcription text.
        3. Zero deadlocks or race conditions.
        """
        mock_whisper_url.side_effect = make_mock_http_error(503, "Service Outage")
        mock_style_url.side_effect = make_mock_http_error(503, "Service Outage")

        num_threads = 10
        results = [None] * num_threads
        exceptions = [None] * num_threads

        def worker(idx):
            try:
                audio = np.ones(16000, dtype=np.float32) * 0.05
                res = self.engine.transcribe(audio, style="casual", engine_mode="groq")
                results[idx] = res
            except Exception as e:
                exceptions[idx] = e

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        t0 = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_time_ms = (time.perf_counter() - t0) * 1000.0

        # Verification
        self.assertEqual(len([e for e in exceptions if e is not None]), 0, f"Exceptions occurred: {exceptions}")
        for idx, res in enumerate(results):
            self.assertIsNotNone(res, f"Thread {idx} produced None")
            self.assertIn("concurrent local hinglish output", res.lower())

        self.assertLess(total_time_ms, 3000.0, f"Concurrent failover took too long: {total_time_ms:.2f}ms")


class TestLocalModePureOfflineAndVRAMIntegrity(unittest.TestCase):
    """
    Empirically verifies that engine_mode == 'local' executes 100% offline
    with 0 MB GPU VRAM consumption.
    """

    def setUp(self):
        self.engine = WhisperEngine(
            model_name="base",
            device="cpu",
            compute_type="int8",
            groq_api_key="gsk_fake_key_local_test",
            engine_mode="local"
        )
        self.mock_local = MagicMock()
        mock_seg = MagicMock()
        mock_seg.text = "Offline pure local text"
        self.mock_local.transcribe.return_value = ([mock_seg], MagicMock())
        self.engine.model = self.mock_local

    @patch("urllib.request.urlopen")
    def test_engine_mode_local_strictly_zero_network_calls(self, mock_urlopen):
        """
        When engine_mode == 'local', neither Stage 1 nor Stage 2 may execute
        any HTTP requests, even when a groq_api_key is present in config.
        """
        # If any network call is attempted, mock will fail the test
        mock_urlopen.side_effect = AssertionError("CRITICAL VIOLATION: Network call was attempted in local engine mode!")

        audio = np.ones(16000, dtype=np.float32) * 0.1

        # 1. Stage 1 check
        res1 = self.engine.transcribe_stage1(audio, engine_mode="local")
        self.assertEqual(res1, "Offline pure local text")
        self.assertEqual(mock_urlopen.call_count, 0)

        # 2. Stage 2 check via StyleEngine
        res2 = StyleEngine.format_two_stage(
            "मैं कल कोड पुश कर दूंगा",
            style="casual",
            engine_mode="local",
            groq_api_key="gsk_fake_key_local_test"
        )
        self.assertIn("main kal code push kar dunga", res2.lower())
        self.assertEqual(mock_urlopen.call_count, 0)

        # 3. Full pipeline check
        res3 = self.engine.transcribe(audio, style="developer", engine_mode="local")
        self.assertEqual(mock_urlopen.call_count, 0)

    def test_zero_gpu_vram_allocation_invariant(self):
        """
        Verifies that device is 'cpu', compute_type is 'int8', and get_vram_usage_mb() returns exactly 0.0 MB.
        If PyTorch and CUDA are installed on this system (e.g. RTX 3060), verifies zero bytes allocated on GPU.
        """
        self.assertEqual(self.engine.device, "cpu")
        self.assertEqual(self.engine.compute_type, "int8")
        self.assertEqual(self.engine.get_vram_usage_mb(), 0.0)

        # Deep check if torch is present
        try:
            import torch
            if torch.cuda.is_available():
                allocated_bytes = torch.cuda.memory_allocated()
                self.assertEqual(allocated_bytes, 0, f"CUDA VRAM was allocated on GPU: {allocated_bytes} bytes!")
        except ImportError:
            pass


class TestHinglishDeveloperModeTransformations(unittest.TestCase):
    """
    Empirically verifies Developer Mode casing transformations, operator conversions,
    and technical token preservation across complex Hinglish developer phrases.
    """

    def test_casing_transformations_in_hinglish(self):
        """Verify camelCase, snake_case, kebab-case, PascalCase, CONSTANT_CASE in Hinglish sentences."""
        cases = [
            # camelCase
            ("bhai camel case user auth token, return fat arrow function", "userAuthToken"),
            ("camel case get user profile by id", "getUserProfileById"),
            ("in camel case total items count", "totalItemsCount"),
            # snake_case
            ("snake case user session token and camel case auth header", "user_session_token"),
            ("as snake case max retry attempts", "max_retry_attempts"),
            ("snake case get current active user", "get_current_active_user"),
            # kebab-case
            ("kebab case primary navigation menu", "primary-navigation-menu"),
            ("in kebab case floating dock capsule", "floating-dock-capsule"),
            # PascalCase
            ("pascal case voice training dialog", "VoiceTrainingDialog"),
            ("pascal case whisper flow engine", "WhisperFlowEngine"),
            # CONSTANT_CASE
            ("constant case api rate limit seconds", "API_RATE_LIMIT_SECONDS"),
            ("screaming snake case default cache timeout", "DEFAULT_CACHE_TIMEOUT"),
        ]

        for phrase, expected_token in cases:
            res = format_developer_mode(phrase)
            self.assertIn(expected_token, res, f"Failed for phrase: '{phrase}' -> got '{res}'")

    def test_spoken_operators_in_hinglish(self):
        """Verify all programming operators convert correctly in conversational Hinglish sentences."""
        operator_cases = [
            ("fat arrow function return karo", "=>"),
            ("arrow function bana do", "=>"),
            ("thin arrow return type", "->"),
            ("strictly equals null check karo", "==="),
            ("triple equals check lagao", "==="),
            ("agar a double equals b", "=="),
            ("if status not equals 200", "!="),
            ("agar value strict not equals undefined", "!=="),
            ("count greater than or equal to 10", ">="),
            ("index less than or equal to length", "<="),
            ("counter plus equals 1 kardo", "+="),
            ("balance minus equals debit amount", "-="),
            ("rate times equals multiplier", "*="),
            ("total divide equals count", "/="),
            ("walrus operator se assign karo", ":="),
            ("colon equals value", ":="),
            ("counter double plus karke loop chalao", "++"),
            ("index double minus karo", "--"),
            ("condition1 logical and condition2", "&&"),
            ("flag1 logical or flag2", "||"),
            ("user address nullish coalescing default city", "??"),
            ("response optional chaining data", "?."),
        ]

        for phrase, expected_symbol in operator_cases:
            res = format_developer_mode(phrase)
            self.assertIn(expected_symbol, res, f"Failed for operator phrase: '{phrase}' -> got '{res}'")

    def test_stutter_filter_masks_repeated_word_operators_anomaly(self):
        """
        EMPIRICAL FINDING / DEFECT REPORT:
        In text_cleaner.py format_developer_mode():
        Line 193: cleaned = re.sub(r'\\b(\\w+)\\s+\\1\\b', r'\\1', cleaned, flags=re.IGNORECASE)
        runs BEFORE operator token replacement (lines 319-331).
        This causes repeated-word spoken operators (explicitly listed in lines 319-331 regexes)
        to be permanently destroyed before they can be matched:
        - 'plus plus' -> collapsed to 'plus' (fails to become '++')
        - 'minus minus' -> collapsed to 'minus' (fails to become '--')
        - 'equals equals' -> collapsed to 'equals' (fails to become '==')
        - 'and and' -> collapsed to 'and' (fails to become '&&')
        - 'or or' -> collapsed to 'or' (fails to become '||')
        """
        # Double plus / double minus work as alternative phrasing
        self.assertEqual(format_developer_mode("counter double plus"), "counter ++")
        self.assertEqual(format_developer_mode("index double minus"), "index --")
        self.assertEqual(format_developer_mode("if a double equals b"), "if a == b")
        self.assertEqual(format_developer_mode("flag logical and check"), "flag && check")
        self.assertEqual(format_developer_mode("flag logical or check"), "flag || check")

        # Empirical proof of masking defect:
        self.assertEqual(format_developer_mode("counter plus plus"), "counter plus")
        self.assertEqual(format_developer_mode("index minus minus"), "index minus")
        self.assertEqual(format_developer_mode("if a equals equals b"), "if a equals b")
        self.assertEqual(format_developer_mode("flag and and check"), "flag and check")
        self.assertEqual(format_developer_mode("flag or or check"), "flag or check")

    def test_delimiters_and_file_tokens_in_hinglish(self):
        """Verify delimiters, file extensions, and console log transforms in Hinglish sentences."""
        token_cases = [
            ("empty parens call karo", "()"),
            ("open paren x close paren", "(x)"),
            ("open brace return data close brace", "{return data}"),
            ("open bracket 0 close bracket", "[0]"),
            ("const config equals dot env file", ".env"),
            ("dot gitignore me add kardo", ".gitignore"),
            ("dot dockerignore inspect karo", ".dockerignore"),
            ("run dot py script", ".py"),
            ("parse dot json payload", ".json"),
            ("export dot ts module", ".ts"),
            ("config dot yaml update karo", ".yaml"),
            ("console dot log error message", "console.log"),
            ("console dot error trace dump karo", "console.error"),
            ("console dot warn warning print karo", "console.warn"),
            ("try catch block me wrap karo", "try/catch"),
            ("async await function define karo", "async/await"),
        ]

        for phrase, expected in token_cases:
            res = format_developer_mode(phrase)
            self.assertIn(expected, res, f"Failed for token phrase: '{phrase}' -> got '{res}'")

    def test_complex_multi_clause_hinglish_developer_sentences(self):
        """Verify complex multi-clause Hinglish sentences with mixed casing, operators, and code tokens."""
        complex_cases = [
            (
                "agar user optional chaining address nullish coalescing default value double equals null hai to console dot log error message kardo",
                ["?.", "??", "==", "console.log"]
            ),
            (
                "const config equals dot env load karo aur try catch block lagao",
                [".env", "try/catch"]
            ),
            (
                "async await function banao jisme response fat arrow handle kare",
                ["async/await", "=>"]
            ),
            (
                "loop me counter plus equals 1 karke array open bracket counter close bracket update karo",
                ["+=", "[", "]"]
            ),
            (
                "snake case user session token and camel case auth header check karo agar not equals empty string to return true",
                ["user_session_token", "authHeader", "!="]
            ),
            (
                "bhai camel case user auth token, return fat arrow function lagao aur semi colon dalo",
                ["userAuthToken", "=>", ";"]
            )
        ]

        for phrase, expected_elements in complex_cases:
            res = format_developer_mode(phrase)
            for elem in expected_elements:
                self.assertIn(elem, res, f"Complex case '{phrase}' missing element '{elem}' in result: '{res}'")

    def test_devanagari_input_in_developer_mode_through_stage2(self):
        """
        Devanagari acoustic transcript in Developer Mode:
        Must romanize Devanagari to Latin script, convert casing/operators, and have zero Devanagari characters.
        """
        hindi_dev_input = "फंक्शन बनाओ camel case get user profile aur fat arrow return karo"
        res = StyleEngine.format_two_stage(hindi_dev_input, style="developer", engine_mode="local")

        # 1. Zero Devanagari
        self.assertFalse(FastDevanagariRomanizer.has_devanagari(res), f"Devanagari remained in output: {res}")
        # 2. Transformed tokens
        self.assertIn("getUserProfile", res)
        self.assertIn("=>", res)
        # 3. Romanized Hindi words
        self.assertIn("return karo", res)


if __name__ == "__main__":
    unittest.main()
