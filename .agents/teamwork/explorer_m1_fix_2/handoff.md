# Handoff Report: Danda Punctuation Failure Modes & Exact Code Recommendations

**Agent**: M1 Fix Explorer 2  
**Handoff Type**: Hard (Task Complete)  
**Scope**: Devanagari Danda (`।` `\u0964`, `॥` `\u0965`) token splitting in `style_engine.py` and boundary lookaround in `voice_profile.py`.

---

## 1. Observation

Direct empirical observations from inspecting code, running unit tests, and executing adversarial benchmarks:

### 1.1 Token Splitting Failure in `style_engine.py`
- **File**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\style_engine.py`
- **Line 282**:
  ```python
  tokens = re.split(r'(\s+|[^\w\u0900-\u097F]+)', text)
  ```
- **Execution Command**:
  ```powershell
  .\.venv\Scripts\python.exe -c "import sys, re; sys.stdout.reconfigure(encoding='utf-8'); text = 'कोड। पुश। सर्वर।'; print('Current split:', re.split(r'(\s+|[^\w\u0900-\u097F]+)', text))"
  ```
- **Verbatim Result**:
  ```
  Current split: ['कोड।', ' ', 'पुश।', ' ', 'सर्वर।']
  ```
- **Adversarial Test Failure** (`tests/test_m1_round2_adversarial.py:208`):
  ```
  FAIL: test_devanagari_sentence_danda_punctuation (tests.test_m1_round2_adversarial.TestDevanagariIntricacies.test_devanagari_sentence_danda_punctuation)
  AssertionError: 5 != 0 : Danda mangled dictionary terms: [('कोड।', 'koda.', 'code.'), ('पुश।', 'pusha.', 'push.'), ('सर्वर।', 'sarvara.', 'server.'), ('कमिट।', 'kamita.', 'commit.'), ('गिटहब।', 'githba.', 'github.')]
  ```

### 1.2 Boundary Lookahead Failure in `voice_profile.py`
- **File**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\voice_profile.py`
- **Lines 220-221**:
  ```python
  lb = r'(?<![\w\u0900-\u097F])' if (k[0].isalnum() or k[0] == '_' or '\u0900' <= k[0] <= '\u097F') else ''
  rb = r'(?![\w\u0900-\u097F])' if (k[-1].isalnum() or k[-1] == '_' or '\u0900' <= k[-1] <= '\u097F') else ''
  ```
- **Execution Command**:
  ```powershell
  .\.venv\Scripts\python.exe -c "from voice_profile import VoiceProfileManager; mgr = VoiceProfileManager.get_instance(); mgr.profile['word_replacements']['सर्वर'] = 'Server'; print('सर्वर। ->', repr(mgr.apply_replacements('सर्वर।'))); print('सर्वर par ->', repr(mgr.apply_replacements('सर्वर par')))"
  ```
- **Verbatim Result**:
  ```
  सर्वर। -> 'सर्वर।'
  सर्वर par -> 'Server par'
  ```
- **Adversarial Test Failure** (`tests/test_m1_round2_adversarial.py:299`):
  ```
  FAIL: test_devanagari_word_followed_by_danda_replacement (tests.test_m1_round2_adversarial.TestLargeDictionaryAndCollisions.test_devanagari_word_followed_by_danda_replacement)
  AssertionError: 'Server' not found in 'सर्वर।' : apply_replacements failed before danda: got 'सर्वर।'
  ```

---

## 2. Logic Chain

1. **Character Class Inclusions (Observation 1.1)**:
   - In Unicode, `U+0964` (`।`) and `U+0965` (`॥`) belong to the Devanagari script block (`U+0900` to `U+097F`).
   - The token splitting regex in `style_engine.py:282` uses `[^\w\u0900-\u097F]+`.
   - Because `\u0964` and `\u0965` are inside `\u0900-\u097F`, the negated character class excludes them from being matched as delimiters.
   - Therefore, `re.split` does not split the danda from the word, generating tokens like `'कोड।'` rather than `['कोड', '।']`.

2. **Dictionary Miss & Medial Schwa Insertion (Observation 1.1)**:
   - In `FastDevanagariRomanizer.transliterate_token`, `word in cls.DEV_COMMON_WORDS` fails because `'कोड।Store'` is not `'कोड'`.
   - The token falls back to algorithmic transliteration. Because the consonant before `।` is followed by another character within the token, line 244 triggers `out.append(base + 'a')` instead of word-final schwa deletion (line 248 `out.append(base)`).
   - Then `।` is mapped to `.` in line 257.
   - Hence `'कोड।Store'` becomes `'koda.'`, `'पुश।Store'` becomes `'pusha.'`, and `'सर्वर।Store'` becomes `'sarvara.'`.

3. **Lookahead Boundary Blocking (Observation 1.2)**:
   - In `voice_profile.py:221`, `rb = r'(?![\w\u0900-\u097F])'` asserts that the character immediately after the replacement key must not be in `[\w\u0900-\u097F]`.
   - Because `\u0964` and `\u0965` are in `\u0900-\u097F`, the negative lookahead matches `।`, treating it as a continuing word character.
   - Consequently, any Devanagari replacement key followed immediately by `।` or `॥` fails the match, and the replacement is blocked.

4. **Resolution via Codepoint Splitting (Observations 1.1 & 1.2)**:
   - The characters preceding `\u0964` in the Devanagari block are `\u0900-\u0963` (vowels, consonants, matras, virama).
   - The characters following `\u0965` in the Devanagari block are `\u0966-\u097F` (digits `०`-`९`, abbreviation sign, candra vowels).
   - Partitioning `\u0900-\u097F` into `\u0900-\u0963` and `\u0966-\u097F` removes only `\u0964` and `\u0965` from word characters:
     - In `style_engine.py`: `[^\w\u0900-\u0963\u0966-\u097F]+` matches `।` and `॥` as delimiters, separating `'कोड'` from `'।'`.
     - In `voice_profile.py`: `(?![\w\u0900-\u0963\u0966-\u097F])` does not match `।` or `॥`, allowing `'सर्वर'` to be replaced before `।`.

---

## 3. Caveats

- In `style_engine.py:transliterate_token`, `\u0970` (Devanagari abbreviation sign `॰`) remains in `\u0966-\u097F` and is treated as a word-internal character (e.g. for abbreviations like `रु॰`). This is correct per Unicode standards.
- In `voice_profile.py`, this analysis focused exclusively on the boundary lookaround logic. Regex scaling for 2,000+ rules is governed by Python's `re` engine and is addressed separately if dictionary pre-compilation is introduced.
- No other caveats.

---

## 4. Conclusion & Exact Drop-In Code Recommendations

Do NOT edit code directly (Explorer read-only constraint). Provide these exact drop-in replacements to the implementer agent:

### 4.1 Drop-In Recommendation 1: `style_engine.py`

**Target File**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\style_engine.py`  
**Target Function**: `FastDevanagariRomanizer.romanize`  
**Lines 281-285**

#### Before:
```python
        tokens = re.split(r'(\s+|[^\w\u0900-\u097F]+)', text)
        result = ''.join(cls.transliterate_token(t) for t in tokens)
        result = re.sub(r'[ \t]+', ' ', result).strip()
        return result
```

#### After:
```python
        tokens = re.split(r'(\s+|[^\w\u0900-\u0963\u0966-\u097F]+)', text)
        result = ''.join(cls.transliterate_token(t) for t in tokens)
        result = re.sub(r'[ \t]+', ' ', result).strip()
        return result
```

#### Secondary Defense-in-Depth (Recommended):
**Target Function**: `FastDevanagariRomanizer.transliterate_token`  
**Lines 232-247**

#### Before:
```python
                base = cls.CONSONANTS[ch]
                if i + 1 < n:
                    nxt = word[i + 1]
                    if nxt == '\u094D':  # Halant / Virama
                        out.append(base)
                        i += 2
                    elif nxt in cls.MATRAS:
                        out.append(base + cls.MATRAS[nxt])
                        i += 2
                    elif nxt in ('\u0902', '\u0901'):  # Anusvara / Candrabindu
                        out.append(base + 'an')
                        i += 2
                    else:
                        out.append(base + 'a')
                        i += 1
```

#### After:
```python
                base = cls.CONSONANTS[ch]
                if i + 1 < n:
                    nxt = word[i + 1]
                    if nxt == '\u094D':  # Halant / Virama
                        out.append(base)
                        i += 2
                    elif nxt in cls.MATRAS:
                        out.append(base + cls.MATRAS[nxt])
                        i += 2
                    elif nxt in ('\u0902', '\u0901'):  # Anusvara / Candrabindu
                        out.append(base + 'an')
                        i += 2
                    elif nxt in ('\u0964', '\u0965'):  # Word-final before Danda
                        out.append(base)
                        i += 1
                    else:
                        out.append(base + 'a')
                        i += 1
```

---

### 4.2 Drop-In Recommendation 2: `voice_profile.py`

**Target File**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\voice_profile.py`  
**Target Function**: `VoiceProfileManager.apply_replacements`  
**Lines 218-223**

#### Before:
```python
        patterns = []
        for k in sorted_keys:
            lb = r'(?<![\w\u0900-\u097F])' if (k[0].isalnum() or k[0] == '_' or '\u0900' <= k[0] <= '\u097F') else ''
            rb = r'(?![\w\u0900-\u097F])' if (k[-1].isalnum() or k[-1] == '_' or '\u0900' <= k[-1] <= '\u097F') else ''
            patterns.append(lb + re.escape(k) + rb)
```

#### After:
```python
        patterns = []
        for k in sorted_keys:
            lb = r'(?<![\w\u0900-\u0963\u0966-\u097F])' if (k[0].isalnum() or k[0] == '_' or ('\u0900' <= k[0] <= '\u0963' or '\u0966' <= k[0] <= '\u097F')) else ''
            rb = r'(?![\w\u0900-\u0963\u0966-\u097F])' if (k[-1].isalnum() or k[-1] == '_' or ('\u0900' <= k[-1] <= '\u0963' or '\u0966' <= k[-1] <= '\u097F')) else ''
            patterns.append(lb + re.escape(k) + rb)
```

---

## 5. Verification Method

To independently verify the recommendations:

### 5.1 Adversarial Danda Tests
Run the specific adversarial danda tests:
```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_m1_round2_adversarial.TestDevanagariIntricacies.test_devanagari_sentence_danda_punctuation
.\.venv\Scripts\python.exe -m unittest tests.test_m1_round2_adversarial.TestLargeDictionaryAndCollisions.test_devanagari_word_followed_by_danda_replacement
```
**Expected Verification Result**:
Both tests pass in `<0.01s` with 0 failures and 0 errors:
- `('कोड।', 'code.')`, `('पुश।', 'push.')`, `('सर्वर।', 'server.')`, `('कमिट।', 'commit.')`, `('गिटहब।', 'github.')` all match expected output.
- `'सर्वर।'` replaces `'सर्वर'` with `'Server'` -> `'Server।'`.

### 5.2 Full Test Suite Regressions
Verify no regressions across existing test suites:
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```
**Expected Verification Result**:
All existing 193 non-adversarial tests pass without failure or timeout.

### 5.3 Invalidation Condition
If `test_devanagari_sentence_danda_punctuation` or `test_devanagari_word_followed_by_danda_replacement` reports `AssertionError`, or any existing unit test in `tests/test_style_engine.py` or `tests/test_calibration_phonetic_memory.py` fails, this conclusion is invalidated.
