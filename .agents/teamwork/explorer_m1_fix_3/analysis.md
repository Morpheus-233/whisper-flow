# Comprehensive Analysis: Stage 3 Contract Failure & Adversarial Test Remediation Blueprint

**Author:** M1 Fix Explorer 3  
**Date:** 2026-10-22  
**Target Milestone:** Whisper Flow Round 2 — Milestone 1 Fix  
**Scope:** `whisper_engine.py`, `style_engine.py`, `voice_profile.py`, `text_cleaner.py`, and `tests/test_m1_round2_adversarial.py`

---

## 1. Executive Summary

Milestone 1 introduces an intelligent Two-Stage speech transcription and styling pipeline. Adversarial stress testing by Challenger 1 (`tests/test_m1_round2_adversarial.py`) revealed **8 failing test cases** across the 20-test adversarial suite. Primary among these is a fundamental architectural contract violation: `WhisperEngine.transcribe()` completely bypassed Stage 3 (`VoiceProfileManager.apply_replacements`) whenever `style=None`. Additional failures stem from Devanagari Unicode edge cases (Candra vowels, visarga, zero-width joiners, danda punctuation token mangling), regex boundary lookahead blockage, 2000-rule regex compilation latency scaling, and pure-punctuation handling in `format_casual_chat`.

This document delivers a root-cause forensic analysis of the Stage 3 contract failure, a comprehensive review of all 20 adversarial tests, and a concrete, file-by-file remediation blueprint proven to achieve **20/20 passing adversarial tests** in 0.22s and **201/201 passing tests** across the entire project repository.

---

## 2. Investigation of Stage 3 Contract Failure Mode

### 2.1 The Architectural Contract
According to `PROJECT.md` (lines 13, 73–77) and `ORIGINAL_REQUEST.md` (line 98):
- **Stage 1 (Acoustic Capture):** `whisper_engine.py:transcribe_stage1` captures raw audio via Groq Cloud (`whisper-large-v3-turbo`) or local CPU int8 (`base`), conditioned on vocabulary biasing `initial_prompt`.
- **Stage 2 (Fast Romanizer & Stylist):** Routes transcript through `StyleEngine.format_two_stage()`. Converts Devanagari to natural Romanized Hinglish in Latin script, preserves technical terms, and enforces style transforms.
- **Stage 3 (Deterministic Exact Match Guarantee):** Always applies `VoiceProfileManager.apply_replacements()` via lookaround regex to guarantee 100% personal dictionary fidelity.
- **Authoritative Contract:** *"Saved personal dictionary words appear with 100% fidelity in output text."* Regardless of whether the caller requested a specific style or left `style=None`, any word in the user's personal phonetic dictionary or custom vocabulary must appear with exact casing and target replacement in the final returned text.

### 2.2 Direct Code Observation
In `whisper_engine.py`, lines 374–405:
```python
374:         # Coordinate with Stage 2 Romanizer and Stage 3 Replacements
375:         if style is not None:
376:             try:
377:                 from voice_profile import VoiceProfileManager
378:                 from style_engine import StyleEngine
379: 
380:                 profile_mgr = VoiceProfileManager.get_instance()
381:                 style_eng = StyleEngine.get_instance()
382: 
383:                 # Stage 2: Fast Romanizer & Stylist
384:                 formatted_text = style_eng.format_two_stage(
385:                     raw_text,
386:                     style=style,
387:                     voice_profile=profile_mgr,
388:                     engine_mode=engine_mode
389:                 )
390: 
391:                 # Stage 3: Deterministic Exact Match Dictionary Guarantee
392:                 final_text = profile_mgr.apply_replacements(formatted_text)
393:                 return final_text
394:             except Exception as e:
395:                 print(f"[WhisperEngine] Stage 2/3 formatting failed: {e}. Returning raw text.")
396:                 return raw_text
397:         else:
398:             # When style is None, Romanize any Devanagari script to Latin Hinglish
399:             try:
400:                 from style_engine import FastDevanagariRomanizer
401:                 if FastDevanagariRomanizer.has_devanagari(raw_text):
402:                     raw_text = FastDevanagariRomanizer.romanize(raw_text)
403:             except Exception:
404:                 pass
405:             return raw_text
```

### 2.3 Root Cause Analysis
1. **Conditional Branching Bypasses Stage 3:** Lines 397–405 branch on `style is None`. In this branch, `whisper_engine.py` attempts optional Devanagari Romanization via `FastDevanagariRomanizer.romanize(raw_text)`, but **never invokes `VoiceProfileManager.apply_replacements`**.
2. **Double Fault in Exception Handling:** In line 396, if an exception occurs during Stage 2 formatting, the handler immediately returns `raw_text`, completely abandoning Stage 3 dictionary replacement.
3. **Downstream Callers Impacted:**
   - `app.py:497`: In the desktop runtime dictation worker, `self.whisper_engine.transcribe(audio_data, initial_prompt=prompt, remove_trailing_stop=False)` is invoked without specifying `style` (defaulting to `style=None`). While `app.py:504` subsequently executed `self.voice_profile.apply_replacements(raw_text)` manually, any external caller or unit test relying on `transcribe()` receives raw unreplaced text.
   - `ui/voice_training_dialog.py:440`: `text = self.whisper_engine.transcribe(audio, initial_prompt=prompt)` is called with `style=None`.
   - `tests/test_m1_round2_adversarial.py:354`: Explicitly asserts `self.assertIn("Kubernetes", self.engine.transcribe(synthetic_audio, style=None))`, causing immediate test failure.
4. **Historical Reason for the Flaw:** In Milestone 1 Round 1, `transcribe()` was solely responsible for acoustic capture. When Two-Stage processing was introduced, the implementer routed `style is not None` to the new pipeline, but left `style=None` as a legacy pass-through to avoid disturbing `test_simulated_zero_gpu_dictation_pipeline` in `test_e2e_workflows.py:206` (which had omitted test fixture isolation for `word_replacements`).

---

## 3. Comprehensive Review of `tests/test_m1_round2_adversarial.py`

The adversarial test harness contains **20 empirical tests** across 5 test classes.
Running `python -m unittest tests/test_m1_round2_adversarial.py` against the unmodified codebase yields **12 PASSES** and **8 FAILURES**.

### 3.1 Test Inventory & Status Matrix

| Class | Test Method | Lines | Focus Area | Status | Root Cause / Failure Mode |
|---|---|---|---|---|---|
| `TestExtremeCodeMixing` | `test_rapid_alternating_code_mixing` | 46–62 | Preserving English tech terms in Hindi sentences | **PASS** | Dict + regex preserves English tokens |
| `TestExtremeCodeMixing` | `test_english_stems_with_hindi_postpositions` | 63–73 | Tech words with markers (ko, par, mein, se) | **PASS** | Casual/Developer styles handle inflections |
| `TestExtremeCodeMixing` | `test_code_mixed_with_urls_and_metrics` | 74–82 | Embedded URLs, sub-350ms metrics, status codes | **PASS** | Protected URL tokenization |
| `TestExtremeCodeMixing` | `test_devanagari_transliterated_technical_terms` | 83–93 | Devanagari tech terms (कोड, सर्वर, पुश) | **PASS** | `DEV_COMMON_WORDS` dictionary mapping |
| `TestDevanagariIntricacies` | `test_devanagari_numerals` | 101–112 | Devanagari numerals (०–९) to Latin digits | **PASS** | `DIGITS` mapping handles all numerals |
| `TestDevanagariIntricacies` | `test_halants_and_complex_ligatures` | 113–133 | Conjuncts, ligatures, 3-consonant clusters | **PASS** | Halant handling (`\u094D`) in algorithmic pass |
| `TestDevanagariIntricacies` | `test_independent_vowels_and_matras` | 134–141 | Combining matras vs independent vowels | **PASS** | Dual vowel/matra tables in Romanizer |
| `TestDevanagariIntricacies` | `test_candra_vowels_containment` | 142–160 | Independent Candra vowels (`ऑ`, `ऍ`, `ॲ`) | **FAIL** | `VOWELS` dict lacks `\u0911`, `\u090D`, `\u0972` |
| `TestDevanagariIntricacies` | `test_visarga_containment` | 161–176 | Standalone Visarga (`ः` `\u0903`) | **FAIL** | `transliterate_token` has no branch for `\u0903` |
| `TestDevanagariIntricacies` | `test_zwj_and_zwnj_containment` | 177–186 | Invisible control codes (`\u200D`, `\u200C`) | **FAIL** | No filtering of ZWJ/ZWNJ in transliteration |
| `TestDevanagariIntricacies` | `test_devanagari_sentence_danda_punctuation` | 187–209 | Sentence danda (`।`, `॥`) tokenization | **FAIL** | Regex `[^\w\u0900-\u097F]+` groups `।` into word |
| `TestCasualChatPunctuationHeavy` | `test_excessive_repeated_punctuation` | 214–230 | Repeated punctuation and trailing periods | **PASS** | `format_casual_chat` cleans repeats & stops |
| `TestCasualChatPunctuationHeavy` | `test_pure_punctuation_inputs` | 231–237 | Pure punctuation inputs (`---`, `***`, `...`) | **FAIL** | `format_casual_chat` lacks empty fallback |
| `TestCasualChatPunctuationHeavy` | `test_urls_and_query_strings` | 238–244 | URLs with query strings & fragments | **PASS** | Protected URL token placeholder logic |
| `TestCasualChatPunctuationHeavy` | `test_contractions_and_apostrophes` | 245–252 | English contractions (`don't`, `it's`) | **PASS** | Regex preserves inner apostrophes |
| `TestLargeDictionaryAndCollisions` | `test_nested_substring_overlap_collision` | 264–281 | Key collision precedence (kubernetes vs kube) | **PASS** | Keys sorted by `len(k)` descending |
| `TestLargeDictionaryAndCollisions` | `test_devanagari_word_followed_by_danda_replacement` | 282–300 | Devanagari key followed by danda (`सर्वर।`) | **FAIL** | Boundary `(?![\w\u0900-\u097F])` blocks before `।` |
| `TestLargeDictionaryAndCollisions` | `test_scaling_up_to_2000_rules` | 301–324 | 2000 rules / 1000 tokens latency scaling | **FAIL** | Regex compile took 1615ms (total 2261ms > 2000ms) |
| `TestTwoStagePipelineContract` | `test_transcribe_with_style_enforces_stage3_replacements` | 337–344 | Stage 3 enforcement when `style="casual"` | **PASS** | Lines 384–392 execute `apply_replacements` |
| `TestTwoStagePipelineContract` | `test_transcribe_without_style_stage3_contract` | 345–358 | Stage 3 enforcement when `style=None` | **FAIL** | Lines 397–405 return `raw_text` directly |

---

## 4. Granular Failure Breakdown & Root Causes

### 4.1 Failure 1: Stage 3 Bypass When `style=None`
- **Test:** `TestTwoStagePipelineContract.test_transcribe_without_style_stage3_contract`
- **Verbatim Error:**
  ```
  AssertionError: 'Kubernetes' not found in 'we deploy on cooper nets today' : transcribe(style=None) failed to apply personal dictionary replacements
  ```
- **Root Cause:** In `whisper_engine.py`, lines 397–405 returned `raw_text` without calling `VoiceProfileManager.get_instance().apply_replacements(raw_text)`.

### 4.2 Failure 2: Devanagari Candra Vowels Leaking into Output
- **Test:** `TestDevanagariIntricacies.test_candra_vowels_containment`
- **Verbatim Error:**
  ```
  AssertionError: 4 != 0 : Independent Candra vowels leaked into output: [('ऑप्शन', 'ऑpshan'), ('ऑनलाइन', 'ऑnalain'), ('ऑब्जेक्ट', 'ऑbjekt'), ('ॲप', 'ॲp')]
  ```
- **Root Cause:** In `style_engine.py`, `FastDevanagariRomanizer.VOWELS` omitted independent Candra vowels:
  - `ऑ` (`\u0911` - Devanagari Letter Candra O)
  - `ऍ` (`\u090D` - Devanagari Letter Candra E)
  - `ॲ` (`\u0972` - Devanagari Letter Candra A)
  When encountering these characters, `transliterate_token` fell into `else: out.append(ch)`, outputting raw Devanagari glyphs.

### 4.3 Failure 3: Standalone Visarga Leaking into Output
- **Test:** `TestDevanagariIntricacies.test_visarga_containment`
- **Verbatim Error:**
  ```
  AssertionError: 3 != 0 : Visarga leaked into output: [('दुःख', 'duःkh'), ('अतः', 'ataः'), ('पुनः', 'punaः')]
  ```
- **Root Cause:** In `style_engine.py`, `transliterate_token` has no branch for `\u0903` (Visarga). It fell into `else: out.append(ch)`, leaving `\u0903` in the output.

### 4.4 Failure 4: Invisible Unicode Control Codes (ZWJ/ZWNJ) Leaking into Output
- **Test:** `TestDevanagariIntricacies.test_zwj_and_zwnj_containment`
- **Verbatim Error:**
  ```
  AssertionError: '\u200d' unexpectedly found in 'k\u200dsh' : ZWJ U+200D leaked into Romanized output
  ```
- **Root Cause:** Zero-Width Joiner (U+200D) and Zero-Width Non-Joiner (U+200C) used in Devanagari conjuncts were not filtered, falling through into `out.append(ch)`.

### 4.5 Failure 5: Devanagari Danda Mangling Word Tokens
- **Test:** `TestDevanagariIntricacies.test_devanagari_sentence_danda_punctuation`
- **Verbatim Error:**
  ```
  AssertionError: 5 != 0 : Danda mangled dictionary terms: [('कोड।', 'koda.', 'code.'), ('पुश।', 'pusha.', 'push.'), ('सर्वर।', 'sarvara.', 'server.'), ('कमिट।', 'kamita.', 'commit.'), ('गिटहब।', 'githba.', 'github.')]
  ```
- **Root Cause:** In `style_engine.py:282`:
  ```python
  tokens = re.split(r'(\s+|[^\w\u0900-\u097F]+)', text)
  ```
  Devanagari Danda (`।` `\u0964`) and Double Danda (`॥` `\u0965`) lie within `\u0900-\u097F`. The split pattern failed to separate `।` from the preceding word token. Consequently, `"कोड।"` was passed as a single token to `transliterate_token`, failing the exact match against `DEV_COMMON_WORDS["कोड"]` and triggering the algorithmic transliterator, which mistakenly added a medial schwa `'a'` (`koda.`, `pusha.`, `sarvara.`).

### 4.6 Failure 6: Danda Blocking Lookahead in `apply_replacements`
- **Test:** `TestLargeDictionaryAndCollisions.test_devanagari_word_followed_by_danda_replacement`
- **Verbatim Error:**
  ```
  AssertionError: 'Server' not found in 'सर्वर।' : apply_replacements failed before danda: got 'सर्वर।'
  ```
- **Root Cause:** In `voice_profile.py:221`:
  ```python
  rb = r'(?![\w\u0900-\u097F])' if (k[-1].isalnum() or k[-1] == '_' or '\u0900' <= k[-1] <= '\u097F') else ''
  ```
  Because `।` (`\u0964`) is in `\u0900-\u097F`, the negative lookahead `(?![\\w\\u0900-\\u097F])` saw `\u0964` and failed to match the word boundary at the end of `"सर्वर"`.

### 4.7 Failure 7: Regex Compilation Bottleneck at 2000 Rules
- **Test:** `TestLargeDictionaryAndCollisions.test_scaling_up_to_2000_rules`
- **Verbatim Error:**
  ```
  AssertionError: 2530.183500000021 not less than 2000.0 : apply_replacements took 2530.18ms, exceeded 2000ms budget
  ```
- **Root Cause:** In `voice_profile.py:218–226`:
  ```python
  patterns = []
  for k in sorted_keys:
      lb = r'(?<![\w\u0900-\u097F])' if ... else ''
      rb = r'(?![\w\u0900-\u097F])' if ... else ''
      patterns.append(lb + re.escape(k) + rb)
  pattern = re.compile(r'(' + '|'.join(patterns) + r')', re.IGNORECASE)
  ```
  Every single pattern had its own independent lookbehind `(?<!...)` and lookahead `(?!...)`. For 2000 rules, Python's `re.compile` had to construct AST and bytecode for 2000 individual lookbehinds and lookaheads, taking **1,615.6 ms** in compile time alone!

### 4.8 Failure 8: Pure Punctuation Not Collapsing to Empty String
- **Test:** `TestCasualChatPunctuationHeavy.test_pure_punctuation_inputs`
- **Verbatim Error:**
  ```
  AssertionError: '---' != '' : Pure punctuation '---' must collapse to empty string, got '---'
  ```
- **Root Cause:** In `text_cleaner.py:format_casual_chat`, step 8 removed dashes only when surrounded by whitespace (`\s+[-—–]+\s+`), and step 11 stripped only trailing `.!?,;:~\``. Input `"---"` or `"***"` without surrounding whitespace or words was never stripped, returning the non-empty string.

---

## 5. Comprehensive Remediation Blueprint

### 5.1 Remediation Architecture Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Remediation Blueprint Flow                            │
├────────────────────────────────┬────────────────────────────────────────────┤
│ Component                      │ Surgical Remediation Action                │
├────────────────────────────────┼────────────────────────────────────────────┤
│ 1. whisper_engine.py           │ Always execute Stage 3 apply_replacements  │
│    (transcribe)                │ across all branches (style != None & None) │
├────────────────────────────────┼────────────────────────────────────────────┤
│ 2. style_engine.py             │ - Add Candra vowels to VOWELS & DEV_WORDS  │
│    (FastDevanagariRomanizer)   │ - Add Visarga (\u0903 -> 'h') branch       │
│                                │ - Filter ZWJ (\u200D) & ZWNJ (\u200C)      │
│                                │ - Delimit danda in split regex (\u0964-65) │
├────────────────────────────────┼────────────────────────────────────────────┤
│ 3. voice_profile.py            │ - Exclude \u0964 and \u0965 from DEV_WORD  │
│    (apply_replacements)        │ - Factor regex into 4 boundary buckets     │
│                                │   (reduces compile time 1615ms -> 131ms)   │
├────────────────────────────────┼────────────────────────────────────────────┤
│ 4. text_cleaner.py             │ - Add pure punctuation guard to return ""  │
│    (format_casual_chat)        │   when no alphanumeric or Devanagari chars │
├────────────────────────────────┼────────────────────────────────────────────┤
│ 5. tests/test_e2e_workflows.py │ - Isolate mgr.profile["word_replacements"] │
│                                │   in test_simulated_zero_gpu_dictation_... │
└────────────────────────────────┴────────────────────────────────────────────┘
```

---

### 5.2 Precise File-by-File Blueprint

#### File 1: `whisper_engine.py`
**Target Method:** `transcribe(self, audio_data, ... style=None, ...)`  
**Line Range:** 374–406  
**Change Description:** Decouple Stage 2 (Romanizer & Stylist) from Stage 3 (Deterministic Replacements). Ensure Stage 3 is unconditionally executed before returning, upholding the 100% dictionary fidelity contract.

```python
<<<< BEFORE (whisper_engine.py:374-406)
        # Coordinate with Stage 2 Romanizer and Stage 3 Replacements
        if style is not None:
            try:
                from voice_profile import VoiceProfileManager
                from style_engine import StyleEngine

                profile_mgr = VoiceProfileManager.get_instance()
                style_eng = StyleEngine.get_instance()

                # Stage 2: Fast Romanizer & Stylist
                formatted_text = style_eng.format_two_stage(
                    raw_text,
                    style=style,
                    voice_profile=profile_mgr,
                    engine_mode=engine_mode
                )

                # Stage 3: Deterministic Exact Match Dictionary Guarantee
                final_text = profile_mgr.apply_replacements(formatted_text)
                return final_text
            except Exception as e:
                print(f"[WhisperEngine] Stage 2/3 formatting failed: {e}. Returning raw text.")
                return raw_text
        else:
            # When style is None, Romanize any Devanagari script to Latin Hinglish
            try:
                from style_engine import FastDevanagariRomanizer
                if FastDevanagariRomanizer.has_devanagari(raw_text):
                    raw_text = FastDevanagariRomanizer.romanize(raw_text)
            except Exception:
                pass
            return raw_text
==== AFTER
        # Stage 2: Fast Romanizer & Stylist
        if style is not None:
            try:
                from voice_profile import VoiceProfileManager
                from style_engine import StyleEngine

                profile_mgr = VoiceProfileManager.get_instance()
                style_eng = StyleEngine.get_instance()

                formatted_text = style_eng.format_two_stage(
                    raw_text,
                    style=style,
                    voice_profile=profile_mgr,
                    engine_mode=engine_mode
                )
            except Exception as e:
                print(f"[WhisperEngine] Stage 2 formatting failed: {e}. Falling back to raw text.")
                formatted_text = raw_text
        else:
            # When style is None, Romanize any Devanagari script to Latin Hinglish
            try:
                from style_engine import FastDevanagariRomanizer
                if FastDevanagariRomanizer.has_devanagari(raw_text):
                    raw_text = FastDevanagariRomanizer.romanize(raw_text)
            except Exception:
                pass
            formatted_text = raw_text

        # Stage 3: Deterministic Exact Match Dictionary Guarantee
        try:
            from voice_profile import VoiceProfileManager
            profile_mgr = VoiceProfileManager.get_instance()
            final_text = profile_mgr.apply_replacements(formatted_text)
            return final_text
        except Exception as e:
            print(f"[WhisperEngine] Stage 3 dictionary replacement failed: {e}. Returning formatted text.")
            return formatted_text
>>>>
```

---

#### File 2: `style_engine.py`
**Target Class:** `FastDevanagariRomanizer`  
**Line Range:** 84–87, 186–188, 215–275, 277–286  
**Change Description:**
1. Add Candra vowels to `VOWELS` (`'ऑ': 'o'`, `'ऍ': 'e'`, `'ॲ': 'a'`).
2. Add common Candra loan words to `DEV_COMMON_WORDS` (`'ऑप्शन': 'option'`, `'ऑनलाइन': 'online'`, `'ऑब्जेक्ट': 'object'`, `'ॲप': 'app'`, `'ऐप': 'app'`).
3. Handle Visarga (`\u0903`) by appending `'h'` in `transliterate_token`.
4. Filter out ZWJ (`\u200D`) and ZWNJ (`\u200C`) in `romanize` and `transliterate_token`.
5. Update `re.split` in `romanize` to exclude Danda (`\u0964`) and Double Danda (`\u0965`) from word characters (`[^\w\u0900-\u0963\u0966-\u097F]+`).

```python
<<<< BEFORE (style_engine.py:84-87)
    VOWELS = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah'
    }
==== AFTER
    VOWELS = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah',
        'ऑ': 'o', 'ऍ': 'e', 'ॲ': 'a'
    }
>>>>

<<<< BEFORE (style_engine.py:186-187)
        'एरर': 'error', 'स्टेशन': 'station', 'चेक': 'check'
    }
==== AFTER
        'एरर': 'error', 'स्टेशन': 'station', 'चेक': 'check',
        'ऑप्शन': 'option', 'ऑनलाइन': 'online', 'ऑब्जेक्ट': 'object', 'ॲप': 'app', 'ऐप': 'app'
    }
>>>>

<<<< BEFORE (style_engine.py:214-216, transliterate_token loop)
        while i < n:
            ch = word[i]
            # Handle Nukta combination
==== AFTER
        while i < n:
            ch = word[i]
            if ch in ('\u200c', '\u200d'):
                i += 1
                continue
            # Handle Nukta combination
>>>>

<<<< BEFORE (style_engine.py:255-258, transliterate_token danda handling)
            elif ch in ('\u0902', '\u0901'):
                out.append('n')
                i += 1
            elif ch in ('\u0964', '\u0965'):  # Danda / Double Danda
                out.append('.')
                i += 1
==== AFTER
            elif ch in ('\u0902', '\u0901'):
                out.append('n')
                i += 1
            elif ch == '\u0903':  # Visarga
                out.append('h')
                i += 1
            elif ch in ('\u0964', '\u0965'):  # Danda / Double Danda
                out.append('.')
                i += 1
>>>>

<<<< BEFORE (style_engine.py:277-286, romanize)
    @classmethod
    def romanize(cls, text: str) -> str:
        """Converts Devanagari script in text to natural Romanized Hinglish."""
        if not text or not cls.has_devanagari(text):
            return text

        tokens = re.split(r'(\s+|[^\w\u0900-\u097F]+)', text)
        result = ''.join(cls.transliterate_token(t) for t in tokens)
        result = re.sub(r'[ \t]+', ' ', result).strip()
        return result
==== AFTER
    @classmethod
    def romanize(cls, text: str) -> str:
        """Converts Devanagari script in text to natural Romanized Hinglish."""
        if not text:
            return ""
        text = text.replace('\u200c', '').replace('\u200d', '')
        if not cls.has_devanagari(text):
            return text

        tokens = re.split(r'(\s+|[^\w\u0900-\u0963\u0966-\u097F]+)', text)
        result = ''.join(cls.transliterate_token(t) for t in tokens)
        result = re.sub(r'[ \t]+', ' ', result).strip()
        return result
>>>>
```

---

#### File 3: `voice_profile.py`
**Target Method:** `VoiceProfileManager.apply_replacements(self, text)`  
**Line Range:** 214–227  
**Change Description:**
1. Define `DEV_WORD_CHAR = r'[\w\u0900-\u0963\u0966-\u097F]'` excluding Danda (`\u0964`) and Double Danda (`\u0965`).
2. Group keys into 4 boundary buckets (`b_both`, `b_start`, `b_end`, `b_none`) while preserving descending length order.
3. Factor out lookaround assertions so the compiled regex has at most 4 lookaround groups instead of 4000 individual lookarounds, cutting compile time from **1,615 ms to 131 ms** (>12x speedup) and keeping memory <3.4 MB.

```python
<<<< BEFORE (voice_profile.py:214-227)
        sorted_keys = sorted([k for k in reps.keys() if k], key=len, reverse=True)
        if not sorted_keys:
            return text

        patterns = []
        for k in sorted_keys:
            lb = r'(?<![\w\u0900-\u097F])' if (k[0].isalnum() or k[0] == '_' or '\u0900' <= k[0] <= '\u097F') else ''
            rb = r'(?![\w\u0900-\u097F])' if (k[-1].isalnum() or k[-1] == '_' or '\u0900' <= k[-1] <= '\u097F') else ''
            patterns.append(lb + re.escape(k) + rb)

        reps_lower = {k.lower(): v for k, v in reps.items()}
        pattern = re.compile(r'(' + '|'.join(patterns) + r')', re.IGNORECASE)
        return pattern.sub(lambda m: reps_lower.get(m.group(0).lower(), m.group(0)), text)
==== AFTER
        sorted_keys = sorted([k for k in reps.keys() if k], key=len, reverse=True)
        if not sorted_keys:
            return text

        dev_word_char = r'[\w\u0900-\u0963\u0966-\u097F]'
        b_both, b_start, b_end, b_none = [], [], [], []
        for k in sorted_keys:
            k_start = (k[0].isalnum() or k[0] == '_' or ('\u0900' <= k[0] <= '\u0963' or '\u0966' <= k[0] <= '\u097F'))
            k_end = (k[-1].isalnum() or k[-1] == '_' or ('\u0900' <= k[-1] <= '\u0963' or '\u0966' <= k[-1] <= '\u097F'))
            esc = re.escape(k)
            if k_start and k_end:
                b_both.append(esc)
            elif k_start:
                b_start.append(esc)
            elif k_end:
                b_end.append(esc)
            else:
                b_none.append(esc)

        parts = []
        if b_both:
            parts.append(rf'(?<!{dev_word_char})(?:' + '|'.join(b_both) + rf')(?!{dev_word_char})')
        if b_start:
            parts.append(rf'(?<!{dev_word_char})(?:' + '|'.join(b_start) + r')')
        if b_end:
            parts.append(r'(?:' + '|'.join(b_end) + rf')(?!{dev_word_char})')
        if b_none:
            parts.append(r'(?:' + '|'.join(b_none) + r')')

        reps_lower = {k.lower(): v for k, v in reps.items()}
        pattern = re.compile(r'(' + '|'.join(parts) + r')', re.IGNORECASE)
        return pattern.sub(lambda m: reps_lower.get(m.group(0).lower(), m.group(0)), text)
>>>>
```

---

#### File 4: `text_cleaner.py`
**Target Method:** `format_casual_chat(text: str) -> str`  
**Line Range:** 43–47  
**Change Description:** Add early guard collapsing pure-punctuation inputs (containing zero alphanumeric or Devanagari characters) to `""`.

```python
<<<< BEFORE (text_cleaner.py:43-47)
    if not text:
        return ""

    cleaned = text.strip()
==== AFTER
    if not text or not re.search(r'[\w\u0900-\u097F]', text):
        return ""

    cleaned = text.strip()
>>>>
```

---

#### File 5: `tests/test_e2e_workflows.py`
**Target Method:** `TestRealWorldWorkloadScenarios.test_simulated_zero_gpu_dictation_pipeline`  
**Line Range:** 185–190, 220–223  
**Change Description:** Isolate test fixtures by clearing `mgr.profile["word_replacements"] = {}` during Step 2 (prior to setting them in Step 3), ensuring test isolation against persistent default profiles on disk while safely restoring them in `finally`.

```python
<<<< BEFORE (tests/test_e2e_workflows.py:185-190)
        mgr = VoiceProfileManager.get_instance()
        original_words = list(mgr.get_custom_words())

        try:
            mgr.profile["custom_words"] = ["WhisperFlow", "CTranslate2", "Hinglish"]
==== AFTER
        mgr = VoiceProfileManager.get_instance()
        original_words = list(mgr.get_custom_words())
        original_reps = dict(mgr.get_replacements())

        try:
            mgr.profile["custom_words"] = ["WhisperFlow", "CTranslate2", "Hinglish"]
            mgr.profile["word_replacements"] = {}
>>>>

<<<< BEFORE (tests/test_e2e_workflows.py:220-222)
        finally:
            mgr.profile["custom_words"] = original_words
==== AFTER
        finally:
            mgr.profile["custom_words"] = original_words
            mgr.profile["word_replacements"] = original_reps
>>>>
```

---

## 6. Empirical Validation Results

Using an in-memory test runner executing against the proposed blueprint:

### 6.1 Adversarial Test Suite (`tests/test_m1_round2_adversarial.py`)
```
Ran 20 tests in 0.220s

OK
[BENCHMARK] apply_replacements (2000 rules, 1000 tokens): 207.38 ms | Peak: 3398.46 KB
Total run: 20 Errors: 0 Failures: 0
```
- **Pass Rate:** 100% (20/20 tests passed).
- **Latency Scaling:** 2000 rules / 1000 tokens completed in **207.38 ms** (Budget: <2000 ms, 90% margin). Peak memory: **3.39 MB** (Budget: <50 MB).

### 6.2 Full Project Regression Suite
```
Ran 201 tests in 3.251s

OK
Total run: 201 Errors: 0 Failures: 0
```
- **Pass Rate:** 100% (201/201 tests passed).
- Zero regressions across existing UI, lifecycle, settings, and pipeline suites.

### 6.3 Automated Hinglish Benchmark (`benchmark_hinglish.py`)
```
================================================================================
  BENCHMARK SUMMARY
  Total Test Cases:       20
  Passed:                 20
  Failed:                 0
  Pass Rate:              100.0%
  Mean CPU Latency:       6.42 ms (Budget: <200 ms)
  Max Latency:            121.26 ms (Budget: <200 ms)
================================================================================
>>> ALL 20 HINGLISH BENCHMARK ASSERTIONS PASSED SUCCESSFULLY! <<<
```

---

## 7. Action Items for Implementer (Worker Agent)

1. Apply proposed diff to `whisper_engine.py:transcribe`.
2. Apply proposed diff to `style_engine.py` (`FastDevanagariRomanizer`).
3. Apply proposed diff to `voice_profile.py` (`apply_replacements`).
4. Apply proposed diff to `text_cleaner.py` (`format_casual_chat`).
5. Apply proposed test fixture isolation diff to `tests/test_e2e_workflows.py`.
6. Run verification commands:
   - `python -m unittest tests/test_m1_round2_adversarial.py`
   - `python -m unittest discover -s tests`
   - `python benchmark_hinglish.py`
