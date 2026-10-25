# Milestone 1 Round 2 Empirical Challenge Report

**Verdict: REQUEST_CHANGES**

---

## 1. Observation

Direct empirical observations from executing adversarial tests against the Milestone 1 codebase (`style_engine.py`, `whisper_engine.py`, `voice_profile.py`, `text_cleaner.py`):

### 1.1 Devanagari Candra Vowels & Visarga Leak into Final Output
In `style_engine.py`, lines 84-87 (`FastDevanagariRomanizer.VOWELS`):
```python
    VOWELS = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah'
    }
```
Independent Candra vowels (`'ऑ'` `\u0911`, `'ऍ'` `\u090D`, `'ॲ'` `\u0972`) and standalone Visarga (`'ः'` `\u0903`) are missing from `VOWELS` and standalone transliteration rules.
Command executed:
```powershell
.\.venv\Scripts\python.exe -c "from style_engine import StyleEngine; se = StyleEngine.get_instance(); print(se.format_two_stage('यह नया ऑप्शन ऑनलाइन अवेलेबल है।', style='casual', engine_mode='local'))"
```
Verbatim Output:
```
yeh naya ऑpshan ऑnalain avelebal hai
```
Verbatim Test Failure (`tests/test_m1_round2_adversarial.py:159`):
```
AssertionError: 4 != 0 : Independent Candra vowels leaked into output: [('ऑप्शन', 'ऑpshan'), ('ऑनलाइन', 'ऑnalain'), ('ऑब्जेक्ट', 'ऑbjekt'), ('ॲप', 'ॲp')]
AssertionError: 3 != 0 : Visarga leaked into output: [('दुःख', 'duःkh'), ('अतः', 'ataः'), ('पुनः', 'punaः')]
```

### 1.2 Sentence-Ending Devanagari Punctuation (`।`, `॥`) Mangles Dictionary Words
In `style_engine.py:282`:
```python
tokens = re.split(r'(\s+|[^\w\u0900-\u097F]+)', text)
```
Because Devanagari Danda (`।` `\u0964`) and Double Danda (`॥` `\u0965`) fall within `\u0900-\u097F`, `[^\w\u0900-\u097F]+` fails to split them from the word. Tokens such as `'कोड।Store'`, `'सर्वर।Store'`, `'पुश।Store'`, `'कमिट।Store'`, `'गिटहब।Store'` are passed into `transliterate_token`.
In `transliterate_token`:
1. `word in cls.DEV_COMMON_WORDS` fails because `'कोड।Store'` is not `'कोड'`.
2. Algorithmic transliteration treats the final consonant before `।` as medial, appending an erroneous schwa `'a'` (`out.append(base + 'a')`).
Command executed:
```powershell
.\.venv\Scripts\python.exe -c "from style_engine import FastDevanagariRomanizer; print('पुश। ->', repr(FastDevanagariRomanizer.romanize('पुश।'))); print('कोड। ->', repr(FastDevanagariRomanizer.romanize('कोड।')))"
```
Verbatim Output:
```
पुश। -> 'pusha.'
कोड। -> 'koda.'
```
Verbatim Test Failure (`tests/test_m1_round2_adversarial.py:208`):
```
AssertionError: 5 != 0 : Danda mangled dictionary terms: [('कोड।', 'koda.', 'code.'), ('पुश।', 'pusha.', 'push.'), ('सर्वर।', 'sarvara.', 'server.'), ('कमिट।', 'kamita.', 'commit.'), ('गिटहब।', 'githba.', 'github.')]
```

### 1.3 Devanagari Danda Blocks Personal Dictionary Replacements
In `voice_profile.py:221`:
```python
rb = r'(?![\w\u0900-\u097F])' if (k[-1].isalnum() or k[-1] == '_' or '\u0900' <= k[-1] <= '\u097F') else ''
```
Because `।` (`\u0964`) and `॥` (`\u0965`) fall within `\u0900-\u097F`, the negative lookahead matches the danda, causing the boundary check to fail.
Command executed:
```powershell
.\.venv\Scripts\python.exe -c "from voice_profile import VoiceProfileManager; mgr = VoiceProfileManager.get_instance(); mgr.profile['word_replacements']['सर्वर'] = 'Server'; print('सर्वर। ->', repr(mgr.apply_replacements('सर्वर।'))); print('सर्वर par ->', repr(mgr.apply_replacements('सर्वर par')))"
```
Verbatim Output:
```
सर्वर। -> 'सर्वर।'
सर्वर par -> 'Server par'
```
Verbatim Test Failure (`tests/test_m1_round2_adversarial.py:299`):
```
AssertionError: 'Server' not found in 'सर्वर।' : apply_replacements failed before danda: got 'सर्वर।'
```

### 1.4 Invisible Unicode Control Codes (`\u200D` ZWJ, `\u200C` ZWNJ) Leak into Output
In `style_engine.py`, `transliterate_token` has no handling for Zero-Width Joiner (U+200D) or Zero-Width Non-Joiner (U+200C).
Command executed:
```powershell
.\.venv\Scripts\python.exe -c "from style_engine import FastDevanagariRomanizer; print(repr(FastDevanagariRomanizer.romanize('क्\u200Dष')))"
```
Verbatim Output:
```
'k\u200dsh'
```
Verbatim Test Failure (`tests/test_m1_round2_adversarial.py:184`):
```
AssertionError: '\u200d' unexpectedly found in 'k\u200dsh' : ZWJ U+200D leaked into Romanized output
```

### 1.5 Interface Contract Violation: `whisper_engine.transcribe` Bypasses Stage 3 when `style=None`
In `whisper_engine.py:375-405`:
```python
        if style is not None:
            # Stage 2: Fast Romanizer & Stylist
            formatted_text = style_eng.format_two_stage(...)
            # Stage 3: Deterministic Exact Match Dictionary Guarantee
            final_text = profile_mgr.apply_replacements(formatted_text)
            return final_text
        else:
            # When style is None, Romanize any Devanagari script to Latin Hinglish
            try:
                from style_engine import FastDevanagariRomanizer
                if FastDevanagariRomanizer.has_devanagari(raw_text):
                    raw_text = FastDevanagariRomanizer.romanize(raw_text)
            except Exception:
                pass
            return raw_text
```
When `style=None` (as called in `app.py:497` and `ui/voice_training_dialog.py:440`), lines 398-405 completely bypass Stage 3 `apply_replacements`.
Command executed:
```powershell
.\.venv\Scripts\python.exe -c "from unittest.mock import MagicMock; from whisper_engine import WhisperEngine; from voice_profile import VoiceProfileManager; import numpy as np; we = WhisperEngine.get_instance(); we.transcribe_stage1 = MagicMock(return_value='we deploy on cooper nets today'); mgr = VoiceProfileManager.get_instance(); mgr.profile['word_replacements']['cooper nets'] = 'Kubernetes'; print(repr(we.transcribe(np.zeros(16000), style=None)))"
```
Verbatim Output:
```
'we deploy on cooper nets today'
```
Verbatim Test Failure (`tests/test_m1_round2_adversarial.py:357`):
```
AssertionError: 'Kubernetes' not found in 'we deploy on cooper nets today' : transcribe(style=None) failed to apply personal dictionary replacements
```

### 1.6 Latency & Memory Scaling Characteristics
Benchmark measurements across operations:
- `FastDevanagariRomanizer`: **0.1411 ms / sentence**, **131.02 KB** peak memory.
- `text_cleaner.format_casual_chat`: **0.201 ms** for 7 benchmark sentences, 0 MB GPU VRAM.
- `VoiceProfileManager.apply_replacements` scaling:
  - 10 rules, 1000 tokens: **19.70 ms** | Peak Mem: **182.30 KB**
  - 100 rules, 1000 tokens: **209.21 ms** | Peak Mem: **656.84 KB**
  - 1000 rules, 1000 tokens: **1081.84 ms** | Peak Mem: **3379.47 KB**
  - 2000 rules, 1000 tokens: **2358.34 ms** | Peak Mem: **6759.34 KB**
  *(For normal profile sizes of <=100 rules on typical 20-word spoken utterances, execution completes in ~4ms. For large dictionaries of 1000-2000 rules, the uncompiled single-pass regex compilation incurs ~1-2s).*

---

## 2. Logic Chain

1. **Script Leakage**:
   - `ORIGINAL_REQUEST.md` (R1 & Acceptance Criteria 1) mandates: *"Hindi audio input produces natural Romanized Hinglish text (Latin alphabet) rather than literal English translations or Devanagari script."*
   - Furthermore, `GROQ_STAGE2_SYSTEM_PROMPT` enforces: *"NEVER output Devanagari script characters in the final output."*
   - By omitting independent Candra vowels (`ऑ`, `ऍ`, `ॲ`) and Visarga (`ः`) from `FastDevanagariRomanizer.VOWELS` (Observation 1.1), common Hindi words and English loan words (`ऑप्शन`, `ऑनलाइन`, `दुःख`, `अतः`) retain raw Devanagari characters.
   - Therefore, the requirement of zero Devanagari characters in output is violated.

2. **Danda Token Mutilation**:
   - Spoken Hindi audio transcribed by Whisper frequently concludes sentences with Devanagari Danda (`।`).
   - By defining token splitting in `style_engine.py:282` as `[^\w\u0900-\u097F]+`, `।` and `॥` are grouped into the word token (Observation 1.2).
   - This prevents dictionary matches in `DEV_COMMON_WORDS` (`'कोड।'` fails `'कोड'`), routing the word to algorithmic transliteration which adds a false medial schwa `'a'` before the punctuation mark.
   - Thus, words like `push` become `pusha.`, `code` becomes `koda.`, and `server` becomes `sarvara.`.

3. **Dictionary Replacement Failure**:
   - `ORIGINAL_REQUEST.md` AC line 98 guarantees: *"Saved personal dictionary words appear with 100% fidelity in output text."*
   - In `voice_profile.py:221`, the right-hand boundary `rb = r'(?![\w\u0900-\u097F])'` treats `।` as a continuation of the word (Observation 1.3).
   - Consequently, any Devanagari term followed by `।` is never replaced, violating the 100% replacement guarantee.

4. **Pipeline Contract Violation**:
   - `PROJECT.md` line 76 and worker handoff line 22 establish that Stage 3 (`apply_replacements`) guarantees 100% dictionary match.
   - In `whisper_engine.py:397-405`, passing `style=None` returns `raw_text` directly without invoking `apply_replacements` (Observation 1.5).
   - Because `app.py` and `ui/voice_training_dialog.py` call `transcribe(audio, style=None)`, any caller relying on `transcribe()` receives unreplaced raw text.

---

## 3. Caveats

- Live Groq Cloud latency was not evaluated against live external network servers due to sandbox API key restrictions (tested using local CPU fallback and circuit breaker simulation; both passed seamlessly with 0 MB GPU VRAM).
- The regex scaling slowdown at 2,000 rules (2.3s) is an extreme stress scenario; typical voice profiles contain fewer than 100 rules, where latency is ~4ms.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone 1 shows excellent foundation in rule-based style conversions, CPU efficiency (<0.15ms Romanization, 0 MB GPU VRAM), and failover handling. However, implementation changes are required before Milestone 1 can be approved:

1. **Fix `FastDevanagariRomanizer.VOWELS`**:
   Add independent Candra vowels (`'ऑ': 'o'`, `'ऍ': 'e'`, `'ॲ': 'a'`) and handle Visarga (`'ः': 'h'`).
2. **Exclude Devanagari Punctuation from Word Token Splitting in `style_engine.py`**:
   Update `FastDevanagariRomanizer.romanize` so `।` (`\u0964`) and `॥` (`\u0965`) are treated as delimiters (`[^\w\u0900-\u0963\u0966-\u097F]+`), allowing dictionary lookup for words like `'कोड'` and `'सर्वर'` when followed by danda.
3. **Fix Lookahead Word Boundary in `voice_profile.py`**:
   Update lookaround regex boundaries to exclude `\u0964` and `\u0965` from word characters: `r'(?![\w\u0900-\u0963\u0966-\u097F])'`.
4. **Filter Unicode Joiners**:
   Strip Zero-Width Joiner (`\u200D`) and Non-Joiner (`\u200C`) in `FastDevanagariRomanizer.transliterate_token`.
5. **Enforce Stage 3 Execution when `style=None` in `whisper_engine.transcribe`**:
   Ensure `VoiceProfileManager.apply_replacements` is executed even when `style is None`, upholding the 100% dictionary fidelity contract.

---

## 5. Verification Method

To independently verify these findings, run the newly added adversarial test harness:

```powershell
.\.venv\Scripts\python.exe -m unittest tests/test_m1_round2_adversarial.py
```

*Expected Verification Output*:
- Test suite executes 20 adversarial tests.
- Isolates the exact 6 failure modes (Candra vowel leak, danda splitting failure, danda replacement blockage, ZWJ leakage, style=None Stage 3 bypass).
- Invalidation condition: All 20 tests in `test_m1_round2_adversarial.py` pass cleanly alongside the existing 161 unit tests and 20 Hinglish benchmark tests.
