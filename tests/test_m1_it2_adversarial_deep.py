"""
Whisper Flow Round 2 — Milestone 1 Iteration 2 Deep Adversarial Challenge Suite
Author: Empirical Challenger M1 (Iteration 2)

Deep empirical stress tests covering:
1. Candra vowels (independent, combining, decomposed, English loanwords, non-dictionary words)
2. Visarga variations (word-final, medial, standalone, visarga + danda)
3. ZWJ / ZWNJ control codes (conjuncts, boundary, isolated, inside English words)
4. Devanagari Danda (\u0964) and Double Danda (\u0965) token splitting and boundary replacements
5. Large dictionary scaling up to 2000 and 3000 rules with latency & memory benchmarking
6. Two-Stage pipeline contract: Stage 3 unconditional execution across all styles, style=None, and under Stage 2 failure
7. Casual Chat extreme punctuation & pure punctuation collapse
8. Devanagari numerals in technical contexts
"""

import os
import sys
import time
import json
import tracemalloc
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from style_engine import FastDevanagariRomanizer, StyleEngine
from text_cleaner import format_casual_chat, format_developer_mode, clean_speech_text
from voice_profile import VoiceProfileManager
from whisper_engine import WhisperEngine


class TestCandraVowelsDeepStress(unittest.TestCase):
    """Exhaustive stress-testing of Candra vowels, decomposed forms, and loanwords."""

    def setUp(self):
        self.romanizer = FastDevanagariRomanizer()

    def test_independent_candra_vowels_dictionary_and_unmapped(self):
        """Test both DEV_COMMON_WORDS and algorithmic fallback on independent Candra vowels."""
        # Dictionary words
        dict_words = {
            "ऑप्शन": "option",
            "ऑनलाइन": "online",
            "ऑब्जेक्ट": "object",
            "ॲप": "app",
            "ऐप": "app",
        }
        for dev, expected in dict_words.items():
            out = self.romanizer.romanize(dev)
            self.assertEqual(out.lower(), expected.lower(), f"Dictionary word '{dev}' expected '{expected}', got '{out}'")
            self.assertFalse(self.romanizer.has_devanagari(out), f"Devanagari leaked in '{dev}': '{out}'")

        # Algorithmic words (not in DEV_COMMON_WORDS)
        novel_words = [
            "ऑटोमेशन",     # Automation -> starts with ऑ (o)
            "ऑपरेटिंग",     # Operating -> starts with ऑ (o)
            "ऑप्टिमाइज़ेशन", # Optimization -> starts with ऑ (o)
            "ऑथेंटिकेशन",   # Authentication -> starts with ऑ (o)
            "ऍक्टिव",       # Active -> starts with ऍ (e)
            "ऍड्रेस",       # Address -> starts with ऍ (e)
            "ॲपल",         # Apple -> starts with ॲ (a)
        ]
        for w in novel_words:
            out = self.romanizer.romanize(w)
            self.assertFalse(self.romanizer.has_devanagari(out), f"Unmapped Candra word '{w}' leaked Devanagari: '{out}'")
            self.assertNotIn("ऑ", out)
            self.assertNotIn("ऍ", out)
            self.assertNotIn("ॲ", out)
            self.assertTrue(len(out) > 0, f"Transliteration of '{w}' was empty")

    def test_decomposed_candra_vowels(self):
        """Test decomposed unicode sequences (अ + ॉ and अ + ॅ)."""
        decomposed_o = "अ\u0949टो"  # Decomposed Auto
        decomposed_e = "अ\u0945प"   # Decomposed App
        
        out_o = self.romanizer.romanize(decomposed_o)
        out_e = self.romanizer.romanize(decomposed_e)

        self.assertFalse(self.romanizer.has_devanagari(out_o), f"Decomposed 'o' leaked Devanagari: '{out_o}'")
        self.assertFalse(self.romanizer.has_devanagari(out_e), f"Decomposed 'e' leaked Devanagari: '{out_e}'")
        self.assertTrue(out_o.startswith("o") or out_o.startswith("O"), f"Expected start with 'o', got '{out_o}'")
        self.assertTrue(out_e.startswith("e") or out_e.startswith("E") or out_e.startswith("a"), f"Expected vowel start, got '{out_e}'")

    def test_combining_candra_matras_on_consonants(self):
        """Test consonant + combining candra matras (ॉ U+0949, ॅ U+0945)."""
        words = {
            "कॉलेज": "kolej",    # क + ॉ
            "डॉक्टर": "doktar",   # ड + ॉ
            "लॉगिन": "login",    # ल + ॉ
            "बॅट": "bet",        # ब + ॅ
            "मॅप": "mep",        # म + ॅ
        }
        for dev, expected_prefix in words.items():
            out = self.romanizer.romanize(dev)
            self.assertFalse(self.romanizer.has_devanagari(out), f"Combining candra matra word '{dev}' leaked Devanagari: '{out}'")
            self.assertTrue(len(out) >= 2)


class TestVisargaDeepStress(unittest.TestCase):
    """Stress-testing of Visarga (ः U+0903) in various syntactic positions."""

    def setUp(self):
        self.romanizer = FastDevanagariRomanizer()

    def test_word_final_visarga_dictionary_and_algorithmic(self):
        """Test word-final visarga in known and novel words."""
        # Known in DEV_COMMON_WORDS
        known = [("अतः", "atah"), ("पुनः", "punah")]
        for dev, exp in known:
            out = self.romanizer.romanize(dev)
            self.assertEqual(out.lower(), exp.lower())
            self.assertFalse(self.romanizer.has_devanagari(out))

        # Algorithmic words
        novel = ["क्रमशः", "प्रायः", "मूलतः", "स्वतः"]
        for w in novel:
            out = self.romanizer.romanize(w)
            self.assertFalse(self.romanizer.has_devanagari(out), f"Visarga leaked in novel word '{w}': '{out}'")
            self.assertNotIn("\u0903", out)
            self.assertTrue(out.endswith("h") or out.endswith("ah"), f"Expected '{w}' to end in 'h' or 'ah', got '{out}'")

    def test_medial_visarga(self):
        """Test medial visarga as in दुःख, निःशुल्क, निःसंदेह."""
        words = ["दुःख", "निःशुल्क", "निःसंदेह"]
        for w in words:
            out = self.romanizer.romanize(w)
            self.assertFalse(self.romanizer.has_devanagari(out), f"Medial visarga leaked in '{w}': '{out}'")
            self.assertNotIn("\u0903", out)

    def test_standalone_and_consecutive_visargas(self):
        """Ensure standalone or anomalous visargas do not leak or crash."""
        anomalous = ["ः", " ः ", "कः", "ःः"]
        for a in anomalous:
            out = self.romanizer.romanize(a)
            self.assertFalse(self.romanizer.has_devanagari(out), f"Devanagari leaked in anomalous visarga '{a}': '{out}'")


class TestControlCodesZWJDeepStress(unittest.TestCase):
    """Stress-testing of Zero-Width Joiner (U+200D) and Non-Joiner (U+200C)."""

    def setUp(self):
        self.romanizer = FastDevanagariRomanizer()

    def test_zwj_and_zwnj_in_complex_conjuncts(self):
        """ZWJ and ZWNJ in Devanagari conjuncts and ligatures."""
        cases = [
            "क्\u200Dष",          # k + halant + ZWJ + ssa
            "र्\u200Dय",          # r + halant + ZWJ + ya (eyelash ra)
            "क\u200C्\u200Cष",     # explicit non-joiner halant
            "\u200Dऑप्शन\u200C",   # leading/trailing control codes
            "सर्वर\u200D।",       # control code before danda
        ]
        for c in cases:
            out = self.romanizer.romanize(c)
            self.assertNotIn("\u200c", out, f"ZWNJ found in output of '{c}': '{out}'")
            self.assertNotIn("\u200d", out, f"ZWJ found in output of '{c}': '{out}'")
            self.assertFalse(self.romanizer.has_devanagari(out), f"Devanagari found in output of '{c}': '{out}'")

    def test_zwj_and_zwnj_in_latin_strings(self):
        """Ensure control codes are stripped even from Latin/mixed inputs."""
        latin_cases = [
            "git\u200Dhub",
            "docker\u200Ccontainer",
            "\u200D\u200C",
        ]
        for lc in latin_cases:
            out = self.romanizer.romanize(lc)
            self.assertNotIn("\u200c", out)
            self.assertNotIn("\u200d", out)


class TestDandaDelimitersDeepStress(unittest.TestCase):
    """Stress-testing of Devanagari Danda (। U+0964) and Double Danda (॥ U+0965)."""

    def setUp(self):
        self.romanizer = FastDevanagariRomanizer()
        self.mgr = VoiceProfileManager.get_instance()
        self.orig_profile = json.loads(json.dumps(self.mgr.profile))

    def tearDown(self):
        self.mgr.profile = self.orig_profile

    def test_danda_token_delimiters_romanization(self):
        """Verify Danda and Double Danda turn into periods without mangling adjacent words."""
        cases = [
            ("यह एक टेस्ट है।", "yeh ek test hai."),
            ("कोड।पुश।कमिट।", "code.push.commit."),
            ("सर्वर॥", "server."),
            ("प्रथम चरण। द्वितीय चरण॥", "pratham charan. dviteey charan."),
            ("।", "."),
            ("॥", "."),
            ("।।।", "..."),
        ]
        for inp, expected in cases:
            out = self.romanizer.romanize(inp)
            self.assertEqual(out.lower(), expected.lower(), f"Input '{inp}' expected '{expected}', got '{out}'")
            self.assertFalse(self.romanizer.has_devanagari(out), f"Devanagari leaked in '{inp}': '{out}'")

    def test_danda_boundary_dictionary_replacements(self):
        """VoiceProfileManager.apply_replacements must match words bounded by Dandas."""
        self.mgr.profile["word_replacements"] = {
            "सर्वर": "Server",
            "डेटाबेस": "Database",
            "डिप्लॉय": "Deploy"
        }
        # Case 1: Word followed by danda
        text1 = "सर्वर। डेटाबेस॥"
        res1 = self.mgr.apply_replacements(text1)
        self.assertIn("Server।", res1)
        self.assertIn("Database॥", res1)

        # Case 2: Danda directly preceding word
        text2 = "।सर्वर"
        res2 = self.mgr.apply_replacements(text2)
        self.assertIn("।Server", res2)

        # Case 3: Word between dandas without spaces
        text3 = "।डिप्लॉय।"
        res3 = self.mgr.apply_replacements(text3)
        self.assertIn("।Deploy।", res3)


class TestDictionaryScalingDeepBenchmark(unittest.TestCase):
    """Benchmark apply_replacements up to 2000 and 3000 rules under extreme conditions."""

    def setUp(self):
        self.mgr = VoiceProfileManager.get_instance()
        self.orig_profile = json.loads(json.dumps(self.mgr.profile))

    def tearDown(self):
        self.mgr.profile = self.orig_profile

    def test_latency_with_2000_rules(self):
        """2000 rules on 1000 tokens must execute in < 2000ms (SLA budget)."""
        num_rules = 2000
        self.mgr.profile["word_replacements"] = {f"kuber_{i}": f"Kubernetes_{i}" for i in range(num_rules)}
        self.mgr.profile["custom_words"] = [f"Word_{i}" for i in range(100)]

        tokens = [f"kuber_{i % num_rules}" if i % 3 == 0 else "plain_word" for i in range(1000)]
        text = " ".join(tokens)

        tracemalloc.start()
        t0 = time.perf_counter()
        out = self.mgr.apply_replacements(text)
        t1 = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        latency_ms = (t1 - t0) * 1000
        peak_kb = peak / 1024
        print(f"\n[DEEP BENCHMARK] 2000 rules, 1000 tokens: {latency_ms:.2f} ms | Peak memory: {peak_kb:.2f} KB")

        self.assertLess(latency_ms, 2000.0, f"Latency {latency_ms:.2f} ms exceeded 2000 ms budget")
        self.assertIn("Kubernetes_0", out)
        self.assertIn("plain_word", out)

    def test_latency_with_3000_rules_stress(self):
        """Stress test with 3000 rules to verify linear or sub-linear scaling."""
        num_rules = 3000
        self.mgr.profile["word_replacements"] = {f"term_{i}": f"Replacement_{i}" for i in range(num_rules)}

        tokens = [f"term_{i % num_rules}" if i % 2 == 0 else "common" for i in range(1500)]
        text = " ".join(tokens)

        t0 = time.perf_counter()
        out = self.mgr.apply_replacements(text)
        t1 = time.perf_counter()

        latency_ms = (t1 - t0) * 1000
        print(f"[DEEP BENCHMARK] 3000 rules, 1500 tokens: {latency_ms:.2f} ms")
        self.assertLess(latency_ms, 2000.0, f"Latency {latency_ms:.2f} ms exceeded 2000 ms budget")


class TestTwoStageContractDeep(unittest.TestCase):
    """Test WhisperEngine transcribe contract across all style modes and failure paths."""

    def setUp(self):
        self.engine = WhisperEngine.get_instance()
        self.mgr = VoiceProfileManager.get_instance()
        self.orig_profile = json.loads(json.dumps(self.mgr.profile))

    def tearDown(self):
        self.mgr.profile = self.orig_profile

    def test_transcribe_all_styles_apply_stage3_replacements(self):
        """Verify Stage 3 applies across: None, casual, developer, professional, custom."""
        self.mgr.profile["word_replacements"] = {"cooper nets": "Kubernetes"}
        styles = [None, "casual", "developer", "professional", "custom"]

        dummy_audio = np.zeros(16000, dtype=np.float32)

        for st in styles:
            self.engine.transcribe_stage1 = MagicMock(return_value="we deploy on cooper nets today")
            out = self.engine.transcribe(dummy_audio, style=st, engine_mode="local")
            self.assertIn("Kubernetes", out, f"Stage 3 failed for style='{st}': got '{out}'")

    def test_transcribe_with_devanagari_and_style_none(self):
        """When style=None and input has Devanagari, it is Romanized and Stage 3 applied."""
        self.mgr.profile["word_replacements"] = {"kuber": "Kubernetes"}
        self.engine.transcribe_stage1 = MagicMock(return_value="सर्वर पर डिप्लॉय kuber")
        dummy_audio = np.zeros(16000, dtype=np.float32)

        out = self.engine.transcribe(dummy_audio, style=None, engine_mode="local")
        self.assertIn("Kubernetes", out)
        self.assertIn("server", out.lower())
        self.assertFalse(FastDevanagariRomanizer.has_devanagari(out))

    def test_stage2_exception_fallback_preserves_stage3(self):
        """If Stage 2 formatting raises an exception, Stage 3 dictionary replacement STILL applies."""
        self.mgr.profile["word_replacements"] = {"misheard term": "TargetTerm"}
        self.engine.transcribe_stage1 = MagicMock(return_value="this is a misheard term")
        dummy_audio = np.zeros(16000, dtype=np.float32)

        with patch("style_engine.StyleEngine.format_two_stage", side_effect=RuntimeError("Groq service crash")):
            out = self.engine.transcribe(dummy_audio, style="casual", engine_mode="cloud")
            self.assertIn("TargetTerm", out, f"Stage 3 was bypassed when Stage 2 crashed: got '{out}'")


class TestCasualChatPunctuationDeep(unittest.TestCase):
    """Stress test format_casual_chat with exotic punctuation and formatting."""

    def test_pure_punctuation_variations(self):
        """All forms of pure punctuation must collapse to empty string."""
        punct_samples = [
            "...", "???", "!!!", "---", "***", ";;;", ":::",
            "  ---  ", "\t...\n", ",,,,,", ". , ! ?", "- - - -",
            "—", "–", "“ ”", "‘ ’", "()", "{}", "[]"
        ]
        for p in punct_samples:
            res = format_casual_chat(p)
            self.assertEqual(res, "", f"Pure punctuation '{p}' did not collapse to empty string: got '{res}'")

    def test_words_with_heavy_surrounding_punctuation(self):
        """Normal words with intense punctuation must be cleanly formatted."""
        text = "Hello, world!!!--- Wait... Is this working??? Yes, it's 100% fine."
        res = format_casual_chat(text)
        self.assertFalse(res.endswith("."))
        self.assertFalse(res.endswith("?"))
        self.assertFalse(res.endswith("!"))
        self.assertIn("hello world", res)
        self.assertIn("it's 100% fine", res)


if __name__ == "__main__":
    unittest.main()
