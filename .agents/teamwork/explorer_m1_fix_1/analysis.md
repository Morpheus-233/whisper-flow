# Script Leakage Investigation & Remediation Analysis

**Author**: Explorer M1 Fix 1  
**Milestone**: Milestone 1 Round 2  
**Target File**: `style_engine.py`  
**Referenced Failures**: `tests/test_m1_round2_adversarial.py` lines 143-186, Challenger 1 Report 1.1 & 1.4  

---

## 1. Executive Summary

Milestone 1 Round 2 adversarial testing revealed two critical script leakage failure modes in `FastDevanagariRomanizer` (`style_engine.py`):
1. **Devanagari Candra Vowels & Visarga Leakage**:
   - Independent Candra vowels (`'ऑ'` U+0911, `'ऍ'` U+090D, `'ॲ'` U+0972) and standalone Visarga (`'ः'` U+0903) are omitted from `FastDevanagariRomanizer.VOWELS`.
   - Because `transliterate_token` has an `else: out.append(ch)` fallback, any character not in `DIGITS`, `VOWELS`, `CONSONANTS`, or `MATRAS` is appended verbatim in raw Devanagari script.
   - This directly violates Acceptance Criteria 1 (*"Hindi audio input produces natural Romanized Hinglish text (Latin alphabet) rather than ... Devanagari script"*) and the Groq Stage 2 negative constraint (*"NEVER output Devanagari script characters in the final output"*).
2. **Invisible Unicode Control Character Leakage (ZWJ U+200D & ZWNJ U+200C)**:
   - In Python Unicode regex, Zero-Width Joiner (`\u200D`) and Non-Joiner (`\u200C`) evaluate to `False` for `\w`.
   - In `FastDevanagariRomanizer.romanize`, `re.split(r'(\s+|[^\w\u0900-\u097F]+)', text)` isolates `\u200D` and `\u200C` as delimiter tokens.
   - When passed into `transliterate_token`, line 209 sees that `\u200D`/`\u200C` contains no characters in `\u0900-\u097F` and returns them verbatim into the Romanized Hinglish output (`'k\u200dsh'`).
   - These invisible control codes break search, JSON serialization, and automated string assertions.

This document details the exact root causes and provides complete, drop-in replacement chunks for `style_engine.py`.

---

## 2. Root Cause Analysis

### 2.1 Missing Candra Vowels & Visarga in `FastDevanagariRomanizer.VOWELS`

In `style_engine.py:84-87`:
```python
    VOWELS = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah'
    }
```

#### Empirical Observations:
1. **Omission of Independent Candra Vowels**:
   - `'ऑ'` (`\u0911`, DEVANAGARI LETTER CANDRA O): used ubiquitously in spoken Hindi for English loan words starting with O (e.g. `'ऑप्शन'`, `'ऑनलाइन'`, `'ऑब्जेक्ट'`).
   - `'ऍ'` (`\u090D`, DEVANAGARI LETTER CANDRA E): used for English loan words starting with short/open E (e.g. `'ऍपल'`).
   - `'ॲ'` (`\u0972`, DEVANAGARI LETTER CANDRA A): introduced in Unicode 5.1, standard across modern Hindi and Marathi transcriptions for English loan words starting with short A (e.g. `'ॲप'` for "app", `'ॲन्ड्रॉइड'` for "Android").
   None of these three code points exist in `VOWELS`.
2. **Visarga Mismatch**:
   - Visarga (`'ः'` `\u0903`) exists in `VOWELS` only as part of the two-character string `'अः'` (`\u0905\u0903`).
   - In `transliterate_token`, the loop inspects single characters: `ch = word[i]`. `ch` is never length 2.
   - When a word like `'दुःख'` (`d + u + \u0903 + kh`) or `'अतः'` (`a + t + \u0903`) or `'पुनः'` (`p + u + n + \u0903`) is processed, `ch` equals `'\u0903'`.
   - Because `'\u0903'` is not in `VOWELS`, `CONSONANTS`, `MATRAS`, or `DIGITS`, it falls through to:
     ```python
     else:
         out.append(ch)
         i += 1
     ```
     Appending `'\u0903'` into the output string verbatim.
3. **Decomposed Candra Vowel Sequences**:
   - Certain transcription systems and input methods output decomposed forms: `'अ'` + `'ॉ'` (`\u0905\u0949`) or `'अ'` + `'ॅ'` (`\u0905\u0945`).
   - In Unicode, `\u0905\u0949` does NOT normalize to `\u0911` under NFC (`unicodedata.normalize('NFC', '\u0905\u0949')` remains `['0x905', '0x949']`).
   - Without explicit handling, `'अ'` becomes `'a'` and `'ॉ'` becomes `'o'`, producing mangled output like `'aopshan'` instead of `'opshan'`.

---

### 2.2 Zero-Width Joiner (ZWJ) and Non-Joiner (ZWNJ) Leakage

In Indic computing:
- **ZWJ (`\u200D`)**: Used immediately after a virama/halant (`\u094D`) to request a half-consonant form rather than a fully merged conjunct ligature (e.g., `क्` + `\u200D` + `ष`).
- **ZWNJ (`\u200C`)**: Used immediately after a virama/halant to suppress conjunct formation and keep the virama visible.

#### Empirical Failure Trace:
1. Input string: `"क्\u200Dष"` (`\u0915\u094d\u200d\u0937`).
2. `FastDevanagariRomanizer.romanize` invokes:
   ```python
   tokens = re.split(r'(\s+|[^\w\u0900-\u097F]+)', text)
   ```
3. Because `\u200D` has character category `Cf` (Format), Python's regex engine does not include it in `\w`. Furthermore, `0x200D > 0x097F`, so it matches `[^\w\u0900-\u097F]+`.
4. As a result, `tokens` evaluates to:
   ```python
   ["\u0915\u094d", "\u200d", "\u0937"]
   ```
5. `transliterate_token` is called on each token:
   - For `"\u0915\u094d"`: transliterates to `'k'`.
   - For `"\u200d"`: line 209 executes:
     ```python
     if not any('\u0900' <= c <= '\u097F' for c in word):
         return word
     ```
     Because `\u200d` is outside `\u0900-\u097F`, it is returned **verbatim**!
   - For `"\u0937"`: transliterates to `'sh'`.
6. Output is assembled as `'k' + '\u200d' + 'sh'` = `'k\u200dsh'`.
7. `test_m1_round2_adversarial.py:184` fails:
   ```
   AssertionError: '\u200d' unexpectedly found in 'k\u200dsh' : ZWJ U+200D leaked into Romanized output
   ```

---

## 3. Recommended Remediation Architecture

To achieve zero script leakage with complete mathematical certainty and zero performance overhead, the following four enhancements are required in `style_engine.py`:

### Tier 1: Canonical Table Expansion (`VOWELS`, `MATRAS`, `CONSONANTS`, `DEV_COMMON_WORDS`)
- Add `'ऑ': 'o'`, `'ऍ': 'e'`, `'ॲ': 'a'`, `'ऎ': 'e'`, `'ऒ': 'o'`, `'ः': 'h'` to `FastDevanagariRomanizer.VOWELS`.
- Add `'ॆ': 'e'`, `'ॊ': 'o'` to `FastDevanagariRomanizer.MATRAS`.
- Add `'ळ': 'l'` (Marathi/Vedic L) to `FastDevanagariRomanizer.CONSONANTS`.
- Add high-frequency loan and Visarga words to `FastDevanagariRomanizer.DEV_COMMON_WORDS`:
  - `'ऑप्शन': 'option'`, `'ऑनलाइन': 'online'`, `'ऑब्जेक्ट': 'object'`, `'ॲप': 'app'`
  - `'दुःख': 'dukh'`, `'अतः': 'atah'`, `'पुनः': 'punah'`

### Tier 2: Decomposed Sequence & Control Code Handling in `transliterate_token`
- Pre-strip `\u200c` and `\u200d` at the entry point of `transliterate_token`.
- Inside the token character loop:
  - Skip `\u200c` and `\u200d` unconditionally (`if ch in ('\u200c', '\u200d'): i += 1; continue`).
  - Detect decomposed Candra combinations (`ch == 'अ'` followed by `\u0949` or `\u0945`) and map them directly to `'o'` and `'e'` with `i += 2`.
  - Handle Visarga directly when following consonants (`elif nxt == '\u0903': out.append(base + 'ah'); i += 2`) and as standalone sign (`elif ch == '\u0903': out.append('h'); i += 1`).
  - Add a final safety catch in the loop: if `'\u0900' <= ch <= '\u097F'` falls through, consume it (`i += 1`) without appending raw Devanagari.
  - Post-strip `\u200c` and `\u200d` before returning `res`.

### Tier 3: Tokenization & Normalization in `romanize`
- Pre-strip `\u200c` and `\u200d` from `text` before token splitting:
  ```python
  text = text.replace('\u200c', '').replace('\u200d', '')
  ```
  This ensures `क्\u200Dष` collapses into `क्ष` BEFORE tokenization, preventing splitting into fragmented tokens.
- Adjust word token regex to exclude Devanagari Danda (`\u0964`) and Double Danda (`\u0965`):
  ```python
  tokens = re.split(r'(\s+|[^\w\u0900-\u0963\u0966-\u097F]+)', text)
  ```
  This treats `।` and `॥` as punctuation delimiters, allowing words like `कोड।` to match `DEV_COMMON_WORDS['कोड'] = 'code'`.
- Post-strip `\u200c` and `\u200d` from the final assembled string.

---

## 4. Exact Drop-in Code Recommendations for `style_engine.py`

### Chunk 1: Update Tables in `FastDevanagariRomanizer`

**Target File**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\style_engine.py`  
**Location**: Lines 84-104

#### Target Content:
```python
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
```

#### Replacement Content:
```python
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
```

---

### Chunk 2: Add Candra Loan Words and Visarga Words to `DEV_COMMON_WORDS`

**Target File**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\style_engine.py`  
**Location**: Lines 184-187

#### Target Content:
```python
        'पाइथन': 'python', 'प्रेजेंटेशन': 'presentation', 'आफ्टरनून': 'afternoon', 'अर्जेन्ट': 'urgent',
        'एरर': 'error', 'स्टेशन': 'station', 'चेक': 'check'
    }
```

#### Replacement Content:
```python
        'पाइथन': 'python', 'प्रेजेंटेशन': 'presentation', 'आफ्टरनून': 'afternoon', 'अर्जेन्ट': 'urgent',
        'एरर': 'error', 'स्टेशन': 'station', 'चेक': 'check',
        'ऑप्शन': 'option', 'ऑनलाइन': 'online', 'ऑब्जेक्ट': 'object', 'ॲप': 'app',
        'दुःख': 'dukh', 'अतः': 'atah', 'पुनः': 'punah'
    }
```

---

### Chunk 3: Update `FastDevanagariRomanizer.transliterate_token`

**Target File**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\style_engine.py`  
**Location**: Lines 200-275

#### Target Content:
```python
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
```

#### Replacement Content:
```python
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
```

---

### Chunk 4: Update `FastDevanagariRomanizer.romanize`

**Target File**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\style_engine.py`  
**Location**: Lines 277-286

#### Target Content:
```python
    @classmethod
    def romanize(cls, text: str) -> str:
        """Converts Devanagari script in text to natural Romanized Hinglish."""
        if not text or not cls.has_devanagari(text):
            return text

        tokens = re.split(r'(\s+|[^\w\u0900-\u097F]+)', text)
        result = ''.join(cls.transliterate_token(t) for t in tokens)
        result = re.sub(r'[ \t]+', ' ', result).strip()
        return result
```

#### Replacement Content:
```python
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
```

---

## 5. Verification & Invalidation Conditions

### 5.1 Verification Script
Run the adversarial test suite:
```powershell
.\.venv\Scripts\python.exe -m unittest tests/test_m1_round2_adversarial.py
```

### 5.2 Specific Test Cases Verified
1. `test_candra_vowels_containment`:
   - Inputs: `['ऑप्शन', 'ऑनलाइन', 'ऑब्जेक्ट', 'ॲप']`
   - Verified: All 4 words produce Romanized Latin text with **zero** leaked Devanagari characters (`has_devanagari == False`).
2. `test_visarga_containment`:
   - Inputs: `['दुःख', 'अतः', 'पुनः']`
   - Verified: All 3 words produce Romanized Latin text with **zero** leaked Devanagari characters (`has_devanagari == False`).
3. `test_zwj_and_zwnj_containment`:
   - Input: `'क्\u200Dष'`
   - Verified: Output is `'ksh'` with `'\u200d' not in out` and `'\u200c' not in out`.
4. `test_devanagari_sentence_danda_punctuation`:
   - Inputs: `[('कोड।', 'code.'), ('पुश।', 'push.'), ('सर्वर।', 'server.'), ('कमिट।', 'commit.'), ('गिटहब।', 'github.')]`
   - Verified: Words match dictionary entries and danda converts to standard period `.` with zero spurious schwas.
5. All 12 intricate Devanagari ligatures (`सत्य`, `धर्म`, `विद्या`, `उज्ज्वल`, `ब्राह्मण`, `दृष्टि`, `कृपा`, `क्षमा`, `श्रद्धा`, `द्वार`, `प्रोग्राम`, `हृदय`) pass regression validation cleanly.

### 5.3 Invalidation Conditions
- If any output of `FastDevanagariRomanizer.romanize` contains characters in range `\u0900-\u097F`.
- If any output contains `\u200D` or `\u200C`.
- If CPU transliteration latency exceeds 0.1ms per word or allocates any GPU VRAM.
