# Milestone 1 Challenge Report: Empirical Stress Testing & Verification

**Verdict**: **DISPROVEN**
*(Baseline Latin Hinglish & English calibration is CONFIRMED, but production readiness for Hindi Devanagari script is DISPROVEN due to 4 reproducible vulnerabilities in Unicode mark stripping, false diff equality, and lookaround boundary collapse).*

---

## 1. Observation

1. **Baseline Unit Tests Execution**:
   - Command: `.\.venv\Scripts\python.exe -m unittest tests/test_speech_calibration.py`
   - Result: `Ran 16 tests in 0.012s - OK`.
   - Verified that all 16 existing tests pass for Latin English and Latin Hinglish strings.

2. **Vulnerability 1 — Devanagari Vowel Sign / Combining Mark Truncation in `strip_punctuation`**:
   - Location: `calibration_engine.py`, lines 34-37:
     ```python
     for w in words:
         cw = re.sub(r"^[^\w]+|[^\w]+$", "", w)
         if cw:
             cleaned_words.append(cw)
     ```
   - Observation: In Python's standard `re` module, `\w` matches characters in Unicode categories `Ll`, `Lu`, `Lt`, `Lo`, `Lm`, `Nd`, and `Pc`. Devanagari vowel signs (matras: `ा`, `ि`, `ी`, `ु`, `ू`, `े`, `ै`, `ो`, `ौ`, `्`, `ं`, etc.) belong to Unicode categories `Mn` (Mark, nonspacing) and `Mc` (Mark, spacing combining).
   - Because `\w` excludes `Mn`/`Mc`, `[^\w]+$` matches and strips the trailing vowel sign from every Hindi word ending in a matra:
     - `'नमस्ते'` -> `'नमस्त'` (strips `\u0947` e-matra)
     - `'करो'` -> `'कर'` (strips `\u094b` o-matra)
     - `'मेरी'` -> `'मेर'` (strips `\u0940` ii-matra)
     - `'पैसा'` -> `'पैस'` (strips `\u093e` aa-matra)
     - `'हैं'` -> `'ह'` (strips `\u0948` ai-matra and `\u0902` anusvara)
     - `'नहीं'` -> `'नह'` (strips `\u0940` ii-matra and `\u0902` anusvara)
   - Impact: When `auto_register_misheard_pairs` runs, target Hindi words registered into `voice_profile.json` are mutilated and corrupt.

3. **Vulnerability 2 — False 100% Equality in Diff Engine for Devanagari Words**:
   - Location: `calibration_engine.py`, lines 16-21 & 96-99:
     ```python
     def clean_token(token: str) -> str:
         return re.sub(r"[^\w\s]", "", token).strip().lower()
     ```
   - Observation: Because `clean_token` removes all `[^\w\s]`, it removes all vowel signs throughout any Hindi word. Distinct words with completely different meanings and grammatical forms reduce to identical strings:
     - `clean_token('कर')` -> `'कर'`
     - `clean_token('करो')` -> `'कर'`
   - Command:
     ```powershell
     .\.venv\Scripts\python.exe -c "import calibration_engine; print(calibration_engine.compute_diff('कर', 'करो'))"
     ```
   - Output:
     `{'accuracy': 100.0, 'target': 'कर', 'heard': 'करो', 'transcribed': 'करो', 'diff': [{'type': 'equal', 'target': 'कर', 'heard': 'करो'}], 'misheard_pairs': [], 'missing_keywords': []}`
   - Result: Completely distinct Hindi words report 100% accuracy and zero misheard pairs.

4. **Vulnerability 3 — Devanagari Prefix Replacement Leak in `apply_replacements`**:
   - Location: `voice_profile.py`, lines 172-174:
     ```python
     lb = r'(?<!\w)' if (k[0].isalnum() or k[0] == '_') else ''
     rb = r'(?!\w)' if (k[-1].isalnum() or k[-1] == '_') else ''
     patterns.append(lb + re.escape(k) + rb)
     ```
   - Observation: For Hindi words ending in a vowel sign (e.g. `'करो'`, `'नमस्ते'`), `k[-1].isalnum()` returns `False` (since Python `str.isalnum()` excludes `Mn`/`Mc`). Therefore, `rb` evaluates to empty string `''`.
   - Command:
     ```powershell
     $env:PYTHONIOENCODING="utf-8"; .\.venv\Scripts\python.exe -c "from voice_profile import VoiceProfileManager; mgr = VoiceProfileManager.get_instance(); mgr.profile['word_replacements'] = {'करो': 'karo'}; print(repr(mgr.apply_replacements('करोगे तो पाओगे')))"
     ```
   - Output: `'karoगे तो पाओगे'`
   - Result: `'करो'` matches as a prefix inside the word `'करोगे'`, replacing it with `'karoगे'`.

5. **Vulnerability 4 — Pure Punctuation False Equality in `compute_diff`**:
   - Location: `calibration_engine.py`, lines 96-108:
     When both target and heard contain only punctuation tokens (e.g. `"..."` and `"???"`), `clean_token` returns `""` for both.
   - Command:
     ```powershell
     .\.venv\Scripts\python.exe -c "import calibration_engine; print(calibration_engine.compute_diff('...', '???'))"
     ```
   - Output:
     `{'accuracy': 100.0, 'target': '...', 'heard': '???', 'transcribed': '???', 'diff': [{'type': 'equal', 'target': '...', 'heard': '???'}], 'misheard_pairs': [], 'missing_keywords': []}`
   - Result: Completely mismatched punctuation strings are reported as 100% equal match.

6. **Confirmed Scalability & Baseline Stability**:
   - Stress test suite `tests/test_empirical_stress_m1.py` ran 15 tests in 0.393s.
   - `apply_replacements` throughput with 2,000 rules on 1,000 tokens executed in 0.3887s with no catastrophic backtracking.
   - Initial prompt biasing strictly truncates within specified `max_chars` budget without crash.
   - Multi-word replacements with special characters (`"c++"`, `"[core]"`, `"cooper nets,"`) function correctly for English words.

---

## 2. Logic Chain

- *Step 1 (Scope & Requirements)*: `ORIGINAL_REQUEST.md` R1 specifies "Bilingual Speech Adaptation & Calibration (English + Hindi/Hinglish)" and `PROJECT.md` configures default multilingual model `"base"` for Hindi/Hinglish speech. Whisper frequently outputs native Devanagari script for Hindi speech.
- *Step 2 (Regex Mechanism)*: Observations 2, 3, and 4 establish that Python's `\w` and `isalnum()` definitions do not cover Unicode non-spacing marks (`Mn`) or combining spacing marks (`Mc`).
- *Step 3 (Causal Link to Data Corruption)*: Because Hindi vowel matras are categorized as `Mn`/`Mc`, `re.sub(r"^[^\w]+|[^\w]+$", "", w)` strips the vowel from the end of every Hindi word ending in a matra (Observation 2). When auto-registering misheard words, corrupt strings like `'नमस्त'` and `'कर'` enter `voice_profile.json`.
- *Step 4 (Causal Link to Accuracy Distortion)*: Because `clean_token` removes all `[^\w\s]`, all vowels inside Hindi words are erased, causing different words like `'कर'` and `'करो'` to produce 100.0% diff accuracy with no misheard pairs detected (Observation 3).
- *Step 5 (Causal Link to Substring Substitution)*: Because `k[-1].isalnum()` is `False` for matras, `voice_profile.py` drops the right-boundary lookaround `(?!\w)`. This allows short words like `'करो'` to substitute inside longer words like `'करोगे'`, producing corrupted hybrid words like `'karoगे'` (Observation 4).
- *Step 6 (Verdict Justification)*: Because the system fails under Hindi Devanagari inputs and pure punctuation edge cases, the claim that Milestone 1 calibration and regex replacement is production-ready for bilingual Hindi/Hinglish speech is `DISPROVEN`.

---

## 3. Caveats

- In `data/calibration_sentences.json`, the 50 Hindi sentences are written exclusively in Latin script (Hinglish, e.g. `"Main thodi der mein call karta hoon."`). On Latin Hinglish, `calibration_engine.py` and `voice_profile.py` function properly without matra issues. However, real-world Whisper transcription with multilingual `"base"` regularly generates Devanagari script for Hindi utterances.
- The 15 tests in `tests/test_empirical_stress_m1.py` pass cleanly while explicitly surfacing these findings and recording their empirical signatures.
- Reviewer is strictly read-only and did not modify `calibration_engine.py` or `voice_profile.py`.

---

## 4. Conclusion

The verdict is **DISPROVEN**.

While Latin Hinglish diffing, dataset loading, and basic English lookaround replacement are verified and functional, Milestone 1 is not production-hardened for bilingual Hindi/Devanagari speech due to:
1. Devanagari matra truncation in `strip_punctuation`
2. Devanagari false 100% equality in `compute_diff`
3. Devanagari prefix match leakage in `apply_replacements`
4. Disjoint pure punctuation false 100% equality in `compute_diff`

### Recommended Mitigations (for Worker):
1. **In `calibration_engine.py`**:
   - In `strip_punctuation`: Replace `r"^[^\w]+|[^\w]+$"` with an approach that preserves Unicode marks (`Mn`, `Mc`) or explicit Devanagari range `\u0900-\u097F`, e.g., strip characters where `unicodedata.category(c).startswith('P')` (or regex `r"^[\s\W\u2000-\u206F!-\/:-@\[-`{-~]+|...$"` protecting `\u0900-\u097F`).
   - In `clean_token`: Do not strip Devanagari matras; allow `\u0900-\u097F` or retain categories `L*`, `N*`, and `M*`.
   - In `compute_diff`: When both `target_norm` and `heard_norm` reduce to empty strings, return `0.0` accuracy unless original trimmed strings are equal.
2. **In `voice_profile.py`**:
   - In `apply_replacements`: Update boundary check to `(k[-1].isalnum() or k[-1] == '_' or '\u0900' <= k[-1] <= '\u097f')` or check `not unicodedata.category(k[-1]).startswith('P')` so right-boundary `(?!\w)` is retained for Hindi words ending in matras.

---

## 5. Verification Method

To independently reproduce all empirical findings:

1. **Run Full Adversarial Stress Harness**:
   ```powershell
   $env:PYTHONIOENCODING="utf-8"
   .\.venv\Scripts\python.exe -m unittest tests/test_empirical_stress_m1.py
   ```
   *Expected output: All 15 tests execute in <0.5s, printing confirmed vulnerability signatures for Devanagari vowel truncation, false diff equality, and prefix leak.*

2. **Direct Reproduction of Devanagari Matra Truncation**:
   ```powershell
   $env:PYTHONIOENCODING="utf-8"
   .\.venv\Scripts\python.exe -c "import calibration_engine; print('नमस्ते ->', repr(calibration_engine.strip_punctuation('नमस्ते')))"
   ```
   *Observed result: `'नमस्ते'` is truncated to `'नमस्त'`.*

3. **Direct Reproduction of Devanagari False Diff Equality**:
   ```powershell
   $env:PYTHONIOENCODING="utf-8"
   .\.venv\Scripts\python.exe -c "import calibration_engine; print(calibration_engine.compute_diff('कर', 'करो')['accuracy'])"
   ```
   *Observed result: `100.0` (False positive equality).*

4. **Direct Reproduction of Devanagari Prefix Leak**:
   ```powershell
   $env:PYTHONIOENCODING="utf-8"
   .\.venv\Scripts\python.exe -c "from voice_profile import VoiceProfileManager; mgr = VoiceProfileManager.get_instance(); mgr.profile['word_replacements'] = {'करो': 'karo'}; print(mgr.apply_replacements('करोगे तो पाओगे'))"
   ```
   *Observed result: `'karoगे तो पाओगे'`.*

5. **Direct Reproduction of Pure Punctuation False Equality**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import calibration_engine; print(calibration_engine.compute_diff('...', '???')['accuracy'])"
   ```
   *Observed result: `100.0` (False positive equality).*
