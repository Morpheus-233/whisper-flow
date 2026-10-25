"""
Whisper Flow Round 2 — Milestone 1 Adversarial Stress Test Suite
Author: Empirical Challenger M1-1

Empirical validation covering:
1. Extreme code-mixed sentences (Devanagari, English tech terms, inflections, URLs).
2. Devanagari numerals, halants, matras, uncommon ligatures, and punctuation (danda, candra vowels, visarga, ZWJ).
3. Punctuation-heavy inputs in Casual Chat style.
4. Large dictionary entries, scaling, and collision testing in apply_replacements.
5. Two-Stage pipeline contract and dictionary fidelity.
"""

import os
import sys
import time
import json
import tracemalloc
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

# Ensure project root is in sys.path
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


class TestExtremeCodeMixing(unittest.TestCase):
    """Stress tests for extreme Hindi-English code-mixing scenarios."""

    def setUp(self):
        self.romanizer = FastDevanagariRomanizer()
        self.style_engine = StyleEngine.get_instance()

    def test_rapid_alternating_code_mixing(self):
        """Mixed Devanagari and English technical tokens in dense alternations."""
        sentence = "मैं कल GitHub repo में नया pull request create करके CI CD pipeline trigger कर दूंगा"
        out = self.romanizer.romanize(sentence)
        
        # Verify English technical tokens are preserved verbatim
        self.assertIn("GitHub", out)
        self.assertIn("repo", out)
        self.assertIn("pull request", out)
        self.assertIn("create", out)
        self.assertIn("CI CD pipeline", out)
        self.assertIn("trigger", out)
        
        # Verify Hindi words are romanized
        self.assertTrue(out.lower().startswith("main kal"))
        self.assertFalse(self.romanizer.has_devanagari(out), f"Leaked Devanagari in output: {out}")

    def test_english_stems_with_hindi_postpositions(self):
        """Technical English words with Hindi grammatical markers (ko, par, mein, se)."""
        sentence = "servers ko restart kiya aur commits ko squash kar diya, branches merge ho gayi"
        casual_out = self.style_engine.format_two_stage(sentence, style="casual", engine_mode="local")
        dev_out = self.style_engine.format_two_stage(sentence, style="developer", engine_mode="local")

        self.assertIn("servers ko restart", casual_out)
        self.assertIn("commits ko squash", casual_out)
        self.assertIn("branches merge", casual_out)
        self.assertFalse(casual_out.endswith("."))

    def test_code_mixed_with_urls_and_metrics(self):
        """Code-mixed text with embedded URLs, timestamps, and performance metrics."""
        text = "API endpoint https://api.groq.com/v1/chat par sub-350ms me 200 OK response aaya"
        casual_out = self.style_engine.format_two_stage(text, style="casual", engine_mode="local")
        
        self.assertIn("https://api.groq.com/v1/chat", casual_out)
        self.assertIn("sub-350ms", casual_out)
        self.assertIn("200 OK", casual_out)

    def test_devanagari_transliterated_technical_terms(self):
        """Devanagari representations of technical words mapped via DEV_COMMON_WORDS."""
        sentence = "कोड पुश कर दिया है और सर्वर पर डिप्लॉय हो गया"
        out = self.romanizer.romanize(sentence)
        
        self.assertIn("code", out.lower())
        self.assertIn("push", out.lower())
        self.assertIn("server", out.lower())
        self.assertIn("deploy", out.lower())
        self.assertFalse(self.romanizer.has_devanagari(out))


class TestDevanagariIntricacies(unittest.TestCase):
    """Stress tests covering Devanagari numerals, halants, matras, ligatures, and signs."""

    def setUp(self):
        self.romanizer = FastDevanagariRomanizer()

    def test_devanagari_numerals(self):
        """Devanagari digits ०-९ conversion to 0-9 in isolation and mixed contexts."""
        cases = [
            ("०१२३४५६७८९", "0123456789"),
            ("१० सर्वर और २० कंटेनर", "10 server aur 20 container"),
            ("रु. ५००", "ru. 500"),
            ("३.१४", "3.14"),
        ]
        for inp, expected in cases:
            out = self.romanizer.romanize(inp)
            self.assertEqual(out, expected, f"Failed on numeral input {inp}")

    def test_halants_and_complex_ligatures(self):
        """Conjuncts, three-consonant clusters, and ligatures."""
        test_words = {
            "सत्य": "saty",
            "धर्म": "dharm",
            "विद्या": "vidya",
            "उज्ज्वल": "ujjval",
            "ब्राह्मण": "brahman",
            "दृष्टि": "drishti",
            "कृपा": "kripa",
            "क्षमा": "kshama",
            "श्रद्धा": "shraddha",
            "द्वार": "dvar",
            "प्रोग्राम": "program",
            "हृदय": "hriday",
        }
        for word, expected_sub in test_words.items():
            out = self.romanizer.romanize(word)
            self.assertFalse(self.romanizer.has_devanagari(out), f"Word '{word}' leaked Devanagari: '{out}'")
            self.assertIn(expected_sub, out.lower(), f"Word '{word}' did not contain expected '{expected_sub}': got '{out}'")

    def test_independent_vowels_and_matras(self):
        """Independent vowels vs combining matras."""
        words = ["सुई", "भाई", "खाएं", "कोई", "नई", "गए", "आइए"]
        for w in words:
            out = self.romanizer.romanize(w)
            self.assertFalse(self.romanizer.has_devanagari(out), f"Word '{w}' leaked Devanagari: '{out}'")
            self.assertTrue(len(out) > 0)

    def test_candra_vowels_containment(self):
        """
        Adversarial test: Independent Candra vowels (ऑ U+0911, ऍ U+090D, ॲ U+0972).
        Whisper outputs these for English loan words starting with O or A (e.g. ऑप्शन, ऑनलाइन, ॲप).
        Verifies whether Devanagari script leaks into the Romanized output.
        """
        loan_words = ["ऑप्शन", "ऑनलाइन", "ऑब्जेक्ट", "ॲप"]
        leaks = []
        for w in loan_words:
            out = self.romanizer.romanize(w)
            if self.romanizer.has_devanagari(out):
                leaks.append((w, out))
        
        # Document empirical observation
        if leaks:
            print(f"[FINDING] Devanagari Candra vowel leak: {leaks}")
        # Rigorous assertion
        self.assertEqual(len(leaks), 0, f"Independent Candra vowels leaked into output: {leaks}")

    def test_visarga_containment(self):
        """
        Adversarial test: Devanagari Visarga (ः U+0903).
        Common in words like दुःख, अतः, पुनः.
        """
        visarga_words = ["दुःख", "अतः", "पुनः"]
        leaks = []
        for w in visarga_words:
            out = self.romanizer.romanize(w)
            if self.romanizer.has_devanagari(out):
                leaks.append((w, out))
        
        if leaks:
            print(f"[FINDING] Devanagari Visarga leak: {leaks}")
        self.assertEqual(len(leaks), 0, f"Visarga leaked into output: {leaks}")

    def test_zwj_and_zwnj_containment(self):
        """
        Adversarial test: Zero Width Joiner (U+200D) and Non-Joiner (U+200C).
        Must not leak invisible control codes into output.
        """
        zwj_text = "क्\u200Dष"
        out = self.romanizer.romanize(zwj_text)
        self.assertNotIn("\u200d", out, "ZWJ U+200D leaked into Romanized output")
        self.assertNotIn("\u200c", out, "ZWNJ U+200C leaked into Romanized output")

    def test_devanagari_sentence_danda_punctuation(self):
        """
        Adversarial test: Sentence-ending Danda (। U+0964) and Double Danda (॥ U+0965).
        Verifies that words preceding danda (e.g. 'पुश।', 'कोड।', 'कमिट।', 'सर्वर।')
        still match DEV_COMMON_WORDS and do not insert broken schwas ('pusha.', 'koda.').
        """
        test_pairs = [
            ("कोड।", "code."),
            ("पुश।", "push."),
            ("सर्वर।", "server."),
            ("कमिट।", "commit."),
            ("गिटहब।", "github."),
        ]
        mismatches = []
        for inp, expected in test_pairs:
            out = self.romanizer.romanize(inp)
            if out.lower() != expected.lower():
                mismatches.append((inp, out, expected))
        
        if mismatches:
            print(f"[FINDING] Devanagari Danda token splitting failures: {mismatches}")
        self.assertEqual(len(mismatches), 0, f"Danda mangled dictionary terms: {mismatches}")


class TestCasualChatPunctuationHeavy(unittest.TestCase):
    """Stress tests for format_casual_chat with extreme and adversarial punctuation."""

    def test_excessive_repeated_punctuation(self):
        cases = [
            ("Hello, world! How are you doing??? I'm good... Wait: what about at 10:30???",
             "hello world how are you doing i'm good wait what about at 10:30"),
            ("Check `whisper_engine.py`! It has 99.9% accuracy; also check config.json: key='value', ok?",
             "check `whisper_engine.py` it has 99.9% accuracy also check config.json key='value' ok"),
            ("Arre yaar, kal meeting hai at 4:30 PM... Please code commit kar do!",
             "arre yaar kal meeting hai at 4:30 PM please code commit kar do"),
        ]
        for text, expected in cases:
            out = format_casual_chat(text)
            self.assertFalse(out.endswith("."), f"Output should not have trailing period: {out}")
            self.assertFalse(out.endswith("!"), f"Output should not have trailing exclamation: {out}")
            self.assertFalse(out.endswith("?"), f"Output should not have trailing question mark: {out}")
            self.assertIn("10:30", out) if "10:30" in text else None
            self.assertIn("99.9%", out) if "99.9%" in text else None

    def test_pure_punctuation_inputs(self):
        """Ensure pure punctuation inputs do not crash or produce bizarre artifacts."""
        cases = ["...", "???!!!", ",,, ... ;;;", "---", "***", "   "]
        for c in cases:
            out = format_casual_chat(c)
            self.assertEqual(out, "", f"Pure punctuation '{c}' must collapse to empty string, got '{out}'")

    def test_urls_and_query_strings(self):
        """URLs with complex query parameters must survive punctuation stripping."""
        url = "https://github.com/openai/whisper?tab=readme-ov-file#installation"
        text = f"Check {url} for docs, ok?"
        out = format_casual_chat(text)
        self.assertIn(url, out, "URL was altered or stripped of valid characters")

    def test_contractions_and_apostrophes(self):
        """Preserve conversational contractions while removing quotation marks."""
        text = "She said, 'Don't worry, it's working!' and smiled."
        out = format_casual_chat(text)
        self.assertIn("don't", out.lower())
        self.assertIn("it's", out.lower())
        self.assertNotIn("'", out.replace("don't", "").replace("it's", ""))


class TestLargeDictionaryAndCollisions(unittest.TestCase):
    """Stress tests for apply_replacements scaling, collisions, and Devanagari boundary rules."""

    def setUp(self):
        self.mgr = VoiceProfileManager.get_instance()
        self.orig_profile = json.loads(json.dumps(self.mgr.profile))

    def tearDown(self):
        self.mgr.profile = self.orig_profile

    def test_nested_substring_overlap_collision(self):
        """Longer keys must take precedence over shorter substrings regardless of insertion order."""
        self.mgr.profile["word_replacements"] = {
            "kube": "KubeTool",
            "kubernetes": "Kubernetes",
            "k": "LetterK",
            "deploy": "DEPLOYMENT"
        }
        text = "we deploy kubernetes using kube and k in production"
        res = self.mgr.apply_replacements(text)
        
        # 'kubernetes' must be 'Kubernetes', not 'KubeToolrnetes'
        self.assertIn("Kubernetes", res)
        self.assertNotIn("KubeToolrnetes", res)
        self.assertIn("KubeTool", res)
        self.assertIn("DEPLOYMENT", res)
        self.assertIn("LetterK", res)

    def test_devanagari_word_followed_by_danda_replacement(self):
        """
        Adversarial test: Devanagari replacement key followed by danda (। U+0964).
        Verifies whether boundary regex (?![\\w\\u0900-\\u097F]) blocks matching before danda.
        """
        self.mgr.profile["word_replacements"] = {
            "सर्वर": "Server",
            "कोड": "Code"
        }
        # Case A: followed by space
        res_space = self.mgr.apply_replacements("सर्वर par")
        self.assertIn("Server par", res_space)

        # Case B: followed by danda
        res_danda = self.mgr.apply_replacements("सर्वर।")
        if "Server" not in res_danda:
            print(f"[FINDING] apply_replacements blocked by Devanagari danda: '{res_danda}'")
        self.assertIn("Server", res_danda, f"apply_replacements failed before danda: got '{res_danda}'")

    def test_scaling_up_to_2000_rules(self):
        """Verify latency and memory scaling with 2000 replacement rules on a 1000-token text."""
        num_rules = 2000
        self.mgr.profile["word_replacements"] = {f"misheard_{i}": f"Target_{i}" for i in range(num_rules)}
        self.mgr.profile["custom_words"] = [f"Word_{i}" for i in range(100)]
        
        test_tokens = [f"misheard_{i % num_rules}" if i % 4 == 0 else "word" for i in range(1000)]
        test_text = " ".join(test_tokens)
        
        tracemalloc.start()
        t0 = time.perf_counter()
        out = self.mgr.apply_replacements(test_text)
        t1 = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        latency_ms = (t1 - t0) * 1000
        peak_kb = peak / 1024
        
        print(f"[BENCHMARK] apply_replacements (2000 rules, 1000 tokens): {latency_ms:.2f} ms | Peak: {peak_kb:.2f} KB")
        # Ensure completion without catastrophic backtracking or OOM (<2.0s budget for 2000 rules / 1000 tokens)
        self.assertLess(latency_ms, 2000.0, f"apply_replacements took {latency_ms:.2f}ms, exceeded 2000ms budget")
        self.assertLess(peak_kb, 50000.0, f"Peak memory {peak_kb:.2f}KB exceeded 50MB budget")


class TestTwoStagePipelineContract(unittest.TestCase):
    """Verifies interface contract and Stage 1 -> Stage 2 -> Stage 3 coordination in WhisperEngine."""

    def setUp(self):
        self.engine = WhisperEngine.get_instance()
        self.mgr = VoiceProfileManager.get_instance()
        self.orig_profile = json.loads(json.dumps(self.mgr.profile))

    def tearDown(self):
        self.mgr.profile = self.orig_profile

    def test_transcribe_with_style_enforces_stage3_replacements(self):
        """When style is provided, Stage 3 apply_replacements MUST be executed."""
        self.mgr.profile["word_replacements"]["cooper nets"] = "Kubernetes"
        self.engine.transcribe_stage1 = MagicMock(return_value="we deploy on cooper nets today")
        
        out = self.engine.transcribe(np.zeros(16000), style="casual", engine_mode="local")
        self.assertIn("Kubernetes", out, "Stage 3 replacements were not applied when style was provided")

    def test_transcribe_without_style_stage3_contract(self):
        """
        Adversarial test: Interface contract specifies that transcribe() guarantees
        100% dictionary match. When style=None is passed, verify whether Stage 3
        apply_replacements is executed.
        """
        self.mgr.profile["word_replacements"]["cooper nets"] = "Kubernetes"
        self.engine.transcribe_stage1 = MagicMock(return_value="we deploy on cooper nets today")
        
        out = self.engine.transcribe(np.zeros(16000), style=None, engine_mode="local")
        if "Kubernetes" not in out:
            print(f"[FINDING] transcribe(style=None) bypassed Stage 3 apply_replacements: got '{out}'")
        self.assertIn("Kubernetes", out, "transcribe(style=None) failed to apply personal dictionary replacements")


if __name__ == "__main__":
    unittest.main()
