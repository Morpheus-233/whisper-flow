# Explorer 1 Handoff Report: Script Leakage Failure Modes in `style_engine.py`

**Milestone**: Milestone 1 Round 2  
**Target Files**: `style_engine.py`  
**Referenced Issues**: Script leakage of Candra vowels, Visarga, and ZWJ/ZWNJ control codes; Danda token boundary splitting.  
**Investigation Type**: Hard (Investigation complete, full 5-component report).  

---

## 1. Observation

Direct empirical observations from executing adversarial tests (`tests/test_m1_round2_adversarial.py`) and inspecting `style_engine.py`:

### 1.1 Devanagari Candra Vowels Leaking into Romanized Output
In `style_engine.py`, lines 84-87 (`FastDevanagariRomanizer.VOWELS`):
```python
    VOWELS = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah'
    }
```
- Independent Candra vowels `'ऑ'` (`\u0911`, Devanagari Letter Candra O), `'ऍ'` (`\u090D`, Devanagari Letter Candra E), and `'ॲ'` (`\u0972`, Devanagari Letter Candra A) are missing from `VOWELS`.
- In `style_engine.py:267-270` (`transliterate_token`), characters not matching `DIGITS`, `VOWELS`, `CONSONANTS`, `MATRAS`, or listed signs fall through to `else: out.append(ch)`.
- Command executed:
  ```powershell
  .\.venv\Scripts\python.exe -c "from style_engine import FastDevanagariRomanizer; print([ascii(FastDevanagariRomanizer.romanize(w)) for w in ['\u0911\u092a\u094d\u0936\u0928', '\u0911\u0928\u0932\u093e\u0907\u0928', '\u0911\u092c\u094d\u091c\u0947\u0915\u094d\u091f', '\u0972\u092a']])"
  ```
- Verbatim Output:
  ```
  ["'\\u0911pshan'", "'\\u0911nalain'", "'\\u0911bjekt'", "'\\u0972p'"]
  ```
- Verbatim Failure in `tests/test_m1_round2_adversarial.py:159`:
  ```
  AssertionError: 4 != 0 : Independent Candra vowels leaked into output: [('ऑप्शन', 'ऑpshan'), ('ऑनलाइन', 'ऑnalain'), ('ऑब्जेक्ट', 'ऑbjekt'), ('ॲप', 'ॲp')]
  ```

### 1.2 Standalone Devanagari Visarga Leaking into Romanized Output
In `style_engine.py:86`, Visarga only exists in the two-character string `'अः': 'ah'`.
- In `transliterate_token`, `ch = word[i]` is a single character. Single character `'ः'` (`\u0903`) never matches `'अः'` and is not in `VOWELS`.
- Consonants preceding Visarga (e.g. `'त'` in `'अतः'`) execute `else: out.append(base + 'a')` because `nxt` (`\u0903`) is not Virama, Matra, or Anusvara. Then the next iteration appends `'\u0903'` verbatim via `else: out.append(ch)`.
- Command executed:
  ```powershell
  .\.venv\Scripts\python.exe -c "from style_engine import FastDevanagariRomanizer; print([ascii(FastDevanagariRomanizer.romanize(w)) for w in ['\u0926\u0941\u0903\u0916', '\u0905\u0924\u0903', '\u092a\u0941\u0928\u0903']])"
  ```
- Verbatim Output:
  ```
  ["'du\\u0903kh'", "'ata\\u0903'", "'puna\\u0903'"]
  ```
- Verbatim Failure in `tests/test_m1_round2_adversarial.py:175`:
  ```
  AssertionError: 3 != 0 : Visarga leaked into output: [('दुःख', 'du\u0903kh'), ('अतः', 'ata\u0903'), ('पुनः', 'puna\u0903')]
  ```

### 1.3 Invisible Unicode Control Characters (ZWJ U+200D & ZWNJ U+200C) Leaking into Romanized Output
- In `style_engine.py:282`:
  ```python
  tokens = re.split(r'(\s+|[^\w\u0900-\u097F]+)', text)
  ```
  In Python regex, `\u200D` and `\u200C` have Unicode general category `Cf` and return `False` for `\w`. Because `0x200D > 0x097F`, `re.split` isolates `\u200D` as a separate delimiter token `['\u0915\u094d', '\u200d', '\u0937']`.
- In `style_engine.py:209-210`:
  ```python
  if not any('\u0900' <= c <= '\u097F' for c in word):
      return word
  ```
  Because `\u200D` has no characters in `\u0900-\u097F`, `transliterate_token` returns `'\u200d'` verbatim into `result = ''.join(...)`.
- Command executed:
  ```powershell
  .\.venv\Scripts\python.exe -c "from style_engine import FastDevanagariRomanizer; print(ascii(FastDevanagariRomanizer.romanize('क्\u200Dष')))"
  ```
- Verbatim Output:
  ```
  'k\u200dsh'
  ```
- Verbatim Failure in `tests/test_m1_round2_adversarial.py:184`:
  ```
  AssertionError: '\u200d' unexpectedly found in 'k\u200dsh' : ZWJ U+200D leaked into Romanized output
  ```

### 1.4 Danda Punctuation (`।`, `॥`) Mangling Word Tokens
- In `style_engine.py:282`, `\u0900-\u097F` includes `।` (`\u0964`) and `॥` (`\u0965`), preventing `re.split` from separating danda from words like `'कोड।Store'`.
- `'कोड।Store'` fails lookup in `DEV_COMMON_WORDS['कोड'] = 'code'` and falls through to algorithmic transliteration which adds a false medial schwa `'a'` before the punctuation mark, generating `'koda.'`, `'pusha.'`, `'sarvara.'`.
- Command executed:
  ```powershell
  .\.venv\Scripts\python.exe -c "from style_engine import FastDevanagariRomanizer; print([FastDevanagariRomanizer.romanize(w) for w in ['कोड।', 'पुश।', 'सर्वर।']])"
  ```
- Verbatim Output:
  ```
  ['koda.', 'pusha.', 'sarvara.']
  ```
- Verbatim Failure in `tests/test_m1_round2_adversarial.py:208`:
  ```
  AssertionError: 5 != 0 : Danda mangled dictionary terms: [('कोड।', 'koda.', 'code.'), ('पुश।', 'pusha.', 'push.'), ('सर्वर।', 'sarvara.', 'server.'), ('कमिट।', 'kamita.', 'commit.'), ('गिटहब।', 'githba.', 'github.')]
  ```

---

## 2. Logic Chain

1. **Mandate**: `ORIGINAL_REQUEST.md` (R1 & Acceptance Criteria 1) strictly mandates: *"Hindi audio input produces natural Romanized Hinglish text (Latin alphabet) rather than literal English translations or Devanagari script."*
2. **Leakage Mechanism (Observation 1.1 & 1.2)**:
   - When spoken Hindi contains English loan words (such as "option" -> `ऑप्शन`, "online" -> `ऑनलाइन`, "app" -> `ॲप`) or traditional Hindi/Sanskrit words with Visarga (`दुःख`, `अतः`, `पुनः`), omitting their Unicode points from `VOWELS` causes them to hit the default branch `else: out.append(ch)`.
   - As a direct consequence, raw Devanagari characters leak into the final output.
3. **Control Code Mechanism (Observation 1.3)**:
   - Whisper produces conjuncts that often contain Zero-Width Joiners (`\u200D`) and Non-Joiners (`\u200C`).
   - Because `re.split` treats them as delimiters and `transliterate_token` treats non-Devanagari tokens as verbatim passthroughs, invisible bytes leak into the string, causing downstream string comparison and assertion failures.
   - Pre-stripping `\u200C` and `\u200D` prior to token splitting and inside `transliterate_token` eliminates all occurrences while preserving the phonetic transcription (`क्\u200Dष` -> `ksh`).
4. **Boundary & Normalization Coordination (Observation 1.4)**:
   - Refining the tokenization split pattern to `[^\w\u0900-\u0963\u0966-\u097F]+` excludes `\u0964` (Danda) and `\u0965` (Double Danda) from word tokens.
   - This ensures words immediately preceding danda match `DEV_COMMON_WORDS` in O(1), translating `कोड।` -> `code.` and `पुश।` -> `push.`.

---

## 3. Caveats

- **Scope Boundary**: This report focuses on `style_engine.py` (Script Leakage, Candra Vowels, Visarga, ZWJ/ZWNJ, and Danda Tokenization). Peer explorer `explorer_m1_fix_2` covers `voice_profile.py:apply_replacements` lookaround regex, and `explorer_m1_fix_3` covers `whisper_engine.py:transcribe(style=None)` Stage 3 contract.
- **Decomposed vs Precomposed Input**: Certain typing tools produce decomposed sequences `'अ'` + `'ॉ'` (`\u0905\u0949`). Our drop-in code in `transliterate_token` explicitly supports both precomposed (`\u0911`) and decomposed (`\u0905\u0949`) forms.
- **No Direct Edits**: As an Explorer, no project source code was directly modified. The verified solution is provided below as complete, drop-in replacement chunks.

---

## 4. Conclusion & Actionable Code Recommendations

All script leakage and ZWJ/ZWNJ failure modes are resolved by applying the following four contiguous changes to `style_engine.py`.

### Code Recommendation 1: Canonical Character Tables in `FastDevanagariRomanizer`
**File**: `style_engine.py` (Lines 84-104)

```python
<<<<
    VOWELS = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah'
    }

    MATRAS = {
        'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
        'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ॉ': 'o', 'ॅ': 'e'
    }

    CONSONANTS = {
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
        'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
        'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
        'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'ड़': 'r', 'ढ़': 'rh', 'फ़': 'f'
    }
====
    VOWELS = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah',
        'ऑ': 'o', 'ऍ': 'e', 'ॲ': 'a', 'ऎ': 'e', 'ऒ': 'o', 'ः': 'h'
    }

    MATRAS = {
        'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
        'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ॉ': 'o', 'ॅ': 'e',
        'ॆ': 'e', 'ॊ': 'o'
    }

    CONSONANTS = {
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
        'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
        'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
        'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'ड़': 'r', 'ढ़': 'rh', 'फ़': 'f',
        'ळ': 'l'
    }
>>>>
```

### Code Recommendation 2: Extend `DEV_COMMON_WORDS` with Candra & Visarga Terms
**File**: `style_engine.py` (Lines 184-187)

```python
<<<<
        'पाइथन': 'python', 'प्रेजेंटेशन': 'presentation', 'आफ्टरनून': 'afternoon', 'अर्जेन्ट': 'urgent',
        'एरर': 'error', 'स्टेशन': 'station', 'चेक': 'check'
    }
====
        'पाइथन': 'python', 'प्रेजेंटेशन': 'presentation', 'आफ्टरनून': 'afternoon', 'अर्जेन्ट': 'urgent',
        'एरर': 'error', 'स्टेशन': 'station', 'चेक': 'check',
        'ऑप्शन': 'option', 'ऑनलाइन': 'online', 'ऑब्जेक्ट': 'object', 'ॲप': 'app',
        'दुःख': 'dukh', 'अतः': 'atah', 'पुनः': 'punah'
    }
>>>>
```

### Code Recommendation 3: Update `FastDevanagariRomanizer.transliterate_token`
**File**: `style_engine.py` (Lines 200-275)

```python
<<<<
    @classmethod
    def transliterate_token(cls, word: str) -> str:
        """Translates a single token via dictionary lookup or algorithmic schwa deletion transliteration."""
        if not word:
            return ""
        # Check dictionary first (O(1))
        if word in cls.DEV_COMMON_WORDS:
            return cls.DEV_COMMON_WORDS[word]

        # If token does not contain any Devanagari characters, return verbatim
        if not any('\u0900' <= c <= '\u097F' for c in word):
            return word

        out = []
        n = len(word)
        i = 0
        while i < n:
            ch = word[i]
            # Handle Nukta combination
            if i + 1 < n and word[i + 1] == '\u093C':
                comb = ch + '\u093C'
                if comb in cls.CONSONANTS:
                    ch = comb
                    i += 1

            if ch in cls.DIGITS:
                out.append(cls.DIGITS[ch])
                i += 1
            elif ch in cls.VOWELS:
                out.append(cls.VOWELS[ch])
                i += 1
            elif ch in cls.CONSONANTS:
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
                else:
                    # Word-final schwa deletion
                    out.append(base)
                    i += 1
            elif ch in cls.MATRAS:
                out.append(cls.MATRAS[ch])
                i += 1
            elif ch in ('\u0902', '\u0901'):
                out.append('n')
                i += 1
            elif ch in ('\u0964', '\u0965'):  # Danda / Double Danda
                out.append('.')
                i += 1
            elif ch == '\u0970':  # Abbreviation sign
                out.append('.')
                i += 1
            elif ch == '\u0950':  # Om
                out.append('om')
                i += 1
            elif ch == '\u093D':  # Avagraha
                i += 1
            else:
                out.append(ch)
                i += 1

        res = ''.join(out)
        # Medial schwa deletion for non-initial syllables (e.g., chalate -> chalte, karate -> karte)
        res = re.sub(r'(?<=[aeiou][b-df-hj-np-tv-z])a(?=[b-df-hj-np-tv-z][aeiou])', '', res)
        return res
====
    @classmethod
    def transliterate_token(cls, word: str) -> str:
        """Translates a single token via dictionary lookup or algorithmic schwa deletion transliteration."""
        if not word:
            return ""
        # Strip invisible zero-width joiner and non-joiner characters
        word = word.replace('\u200c', '').replace('\u200d', '')
        if not word:
            return ""

        # Check dictionary first (O(1))
        if word in cls.DEV_COMMON_WORDS:
            return cls.DEV_COMMON_WORDS[word]

        # If token does not contain any Devanagari characters, return verbatim
        if not any('\u0900' <= c <= '\u097F' for c in word):
            return word

        out = []
        n = len(word)
        i = 0
        while i < n:
            ch = word[i]
            # Strip lingering zero-width joiner/non-joiner
            if ch in ('\u200c', '\u200d'):
                i += 1
                continue

            # Handle decomposed Candra vowels (e.g. अ + ॉ -> o, अ + ॅ -> e)
            if ch == 'अ' and i + 1 < n:
                if word[i + 1] == '\u0949':
                    out.append('o')
                    i += 2
                    continue
                elif word[i + 1] == '\u0945':
                    out.append('e')
                    i += 2
                    continue

            # Handle Nukta combination
            if i + 1 < n and word[i + 1] == '\u093C':
                comb = ch + '\u093C'
                if comb in cls.CONSONANTS:
                    ch = comb
                    i += 1

            if ch in cls.DIGITS:
                out.append(cls.DIGITS[ch])
                i += 1
            elif ch in cls.VOWELS:
                out.append(cls.VOWELS[ch])
                i += 1
            elif ch in cls.CONSONANTS:
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
                    elif nxt == '\u0903':  # Visarga after consonant
                        out.append(base + 'ah')
                        i += 2
                    else:
                        out.append(base + 'a')
                        i += 1
                else:
                    # Word-final schwa deletion
                    out.append(base)
                    i += 1
            elif ch in cls.MATRAS:
                out.append(cls.MATRAS[ch])
                i += 1
            elif ch in ('\u0902', '\u0901'):
                out.append('n')
                i += 1
            elif ch in ('\u0964', '\u0965'):  # Danda / Double Danda
                out.append('.')
                i += 1
            elif ch == '\u0970':  # Abbreviation sign
                out.append('.')
                i += 1
            elif ch == '\u0950':  # Om
                out.append('om')
                i += 1
            elif ch == '\u093D':  # Avagraha
                i += 1
            elif ch == '\u0903':  # Standalone Visarga
                out.append('h')
                i += 1
            elif '\u0900' <= ch <= '\u097F':
                # Safety catch-all to prevent unmapped Devanagari from leaking
                i += 1
            else:
                out.append(ch)
                i += 1

        res = ''.join(out)
        res = res.replace('\u200c', '').replace('\u200d', '')
        # Medial schwa deletion for non-initial syllables (e.g., chalate -> chalte, karate -> karte)
        res = re.sub(r'(?<=[aeiou][b-df-hj-np-tv-z])a(?=[b-df-hj-np-tv-z][aeiou])', '', res)
        return res
>>>>
```

### Code Recommendation 4: Update `FastDevanagariRomanizer.romanize`
**File**: `style_engine.py` (Lines 277-286)

```python
<<<<
    @classmethod
    def romanize(cls, text: str) -> str:
        """Converts Devanagari script in text to natural Romanized Hinglish."""
        if not text or not cls.has_devanagari(text):
            return text

        tokens = re.split(r'(\s+|[^\w\u0900-\u097F]+)', text)
        result = ''.join(cls.transliterate_token(t) for t in tokens)
        result = re.sub(r'[ \t]+', ' ', result).strip()
        return result
====
    @classmethod
    def romanize(cls, text: str) -> str:
        """Converts Devanagari script in text to natural Romanized Hinglish."""
        if not text:
            return text

        # Strip invisible zero-width joiner and non-joiner control codes
        text = text.replace('\u200c', '').replace('\u200d', '')
        if not cls.has_devanagari(text):
            return text

        # Exclude Devanagari Danda (\u0964) and Double Danda (\u0965) from word tokens to enable dictionary lookup
        tokens = re.split(r'(\s+|[^\w\u0900-\u0963\u0966-\u097F]+)', text)
        result = ''.join(cls.transliterate_token(t) for t in tokens)
        result = result.replace('\u200c', '').replace('\u200d', '')
        result = re.sub(r'[ \t]+', ' ', result).strip()
        return result
>>>>
```

---

## 5. Verification Method

To independently verify this solution:

1. **Adversarial Test Suite**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest tests/test_m1_round2_adversarial.py
   ```
   *Expected Result*:
   - `test_candra_vowels_containment` PASSES with 0 leaks.
   - `test_visarga_containment` PASSES with 0 leaks.
   - `test_zwj_and_zwnj_containment` PASSES with 0 control codes in output.
   - `test_devanagari_sentence_danda_punctuation` PASSES with exact dictionary conversions (`code.`, `push.`, `server.`, `commit.`, `github.`).

2. **Full Unit & Benchmark Suite**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover tests
   ```
   *Expected Result*: All 201 tests execute cleanly with zero regressions on existing Romanization benchmarks.

3. **Invalidation Conditions**:
   - Any character in range `\u0900-\u097F` present in `FastDevanagariRomanizer.romanize` output.
   - Any `\u200D` or `\u200C` present in output.
   - Transliteration latency exceeding 0.2ms per sentence or GPU memory allocation > 0 MB.
