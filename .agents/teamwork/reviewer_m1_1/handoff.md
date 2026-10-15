# Reviewer & Adversarial Critic Report: Milestone 1

## Review Summary

**Verdict**: **REQUEST_CHANGES**

**Integrity Audit**: PASSED (No fake implementations, facades, hardcoded test answers, or integrity violations detected).
**Functionality Audit**: Core diff calculation, lookaround regex engine, and dialog opening latency satisfy requirements. However, 3 Major findings and 2 Minor findings require remediation before Milestone 1 can be signed off.

---

## 1. Observation

1. **Unit Test Pass Status**:
   - Command: `.\.venv\Scripts\python.exe -m unittest tests/test_speech_calibration.py`
   - Result: `Ran 16 tests in 0.008s` / `OK`.
   - Command: `.\.venv\Scripts\python.exe -m unittest tests/test_e2e_workflows.py`
   - Result: `Ran 5 tests in 0.288s` / `OK`.
   - Command: `.\.venv\Scripts\python.exe -m unittest tests/test_m1_challenger2_stress.py`
   - Result: `Ran 11 tests in 0.395s` / `OK`.

2. **Dataset Semantic Defect (Sentence #87)**:
   - Path: `data/calibration_sentences.json` lines 845-853:
     ```json
     {
       "id": 87,
       "category": "hindi_hinglish",
       "text": "Client ko demo dikhane se pehle edge cases thoroughly test kar lena.",
       "phonetic_keywords": [
         "client demo",
         "edge cases",
         "thoroughly"
       ]
     }
     ```
   - Observed: The keyword `"client demo"` does not exist in the sentence text due to the intrusive particle `"ko"` (`"Client ko demo..."`).
   - When spoken accurately: `compute_diff` produces `missing_keywords: ['client demo']`, creating an unavoidable false-positive penalty for the user.

3. **Race Condition in VoiceTrainingDialog Async Transcription**:
   - Path: `ui/voice_training_dialog.py` lines 428-450:
     ```python
     def transcribe():
         prompt = self.profile_mgr.get_initial_prompt()
         text = self.whisper_engine.transcribe(audio, initial_prompt=prompt)
         ...
         target_item = self.filtered_dataset[self.current_sentence_idx]
         target_text = target_item.get("text", "")
         keywords = target_item.get("phonetic_keywords", [])

         diff_res = compute_diff(target_text, text, keywords)
     ```
   - Lines 425-427 disable only `record_sentence_btn`. `next_sentence_btn`, `prev_sentence_btn`, and `category_combo` remain enabled.
   - If a user clicks `Next Sentence` during the 1-2 second transcription window, `self.current_sentence_idx` increments. When `transcribe` evaluates line 436, it compares the spoken audio against the *next* sentence instead of the recorded sentence.

4. **Interface Contract Violation in `studio_server.py`**:
   - `PROJECT.md` lines 66-72 specify:
     ```markdown
     ### calibration_engine.py ↔ ui/voice_training_dialog.py & studio_server.py
     - compute_diff(target_text: str, transcribed_text: str, phonetic_keywords: list[str] | None = None) -> dict:
       Requirements: Words in misheard_pairs must be stripped of punctuation (e.g. "hoon" instead of "hoon.").
     ```
   - Path: `studio_server.py` lines 75-130 contains a duplicate unpatched definition of `compute_diff` which still executes:
     ```python
     elif tag == "replace":
         t_chunk = " ".join(target_tokens[i1:i2])
         h_chunk = " ".join(heard_tokens[j1:j2])
         diff.append({"type": "replace", "target": t_chunk, "heard": h_chunk})
         if t_chunk and h_chunk:
             misheard_pairs.append({"heard": h_chunk, "target": t_chunk})
     ```
   - Observed: `studio_server.py` does not import `calibration_engine.py`. Web companion users will still suffer from trailing punctuation leakage into `voice_profile.json`.

5. **Keyword Substring False-Negative in `calibration_engine.py`**:
   - Path: `calibration_engine.py` lines 142-147:
     ```python
     clean_transcript = " ".join(re.sub(r"[^\w\s]", "", transcribed_text).lower().split())
     missing_keywords = []
     for kw in phonetic_keywords:
         kw_norm = " ".join(re.sub(r"[^\w\s]", "", kw).lower().split())
         if kw_norm and kw_norm not in clean_transcript:
             missing_keywords.append(kw)
     ```
   - Tested: `compute_diff("I have a cat", "I catch the ball", phonetic_keywords=["cat"])`
   - Observed: `missing_keywords` returned `[]` because `"cat"` is a naive substring of `"catch"`.

6. **Worker Verification Command #2 Fails Without Pre-Seeding**:
   - Worker handoff verification command:
     `.\.venv\Scripts\python.exe -c "from voice_profile import VoiceProfileManager; mgr = VoiceProfileManager.get_instance(); assert mgr.apply_replacements('I manage cooper nets, in cloud') == 'I manage Kubernetes in cloud'; print('Regex verified!')"`
   - Output: `AssertionError` (Exit code 1).
   - Reason: `"cooper nets,"` is not in `DEFAULT_PROFILE` or `voice_profile.json`. The underlying regex implementation in `voice_profile.py` works, but the verification command fails out of the box unless the key is pre-populated.

---

## 2. Logic Chain

1. **Dataset Integrity**: From Observation 2, sentence #87 pairs `"Client ko demo dikhane..."` with `"client demo"`. In Hindi/Hinglish syntax, the postposition `"ko"` separates `"Client"` and `"demo"`. Because `compute_diff` checks for exact phrase containment, `"client demo"` is guaranteed to fail every time sentence 87 is transcribed, corrupting calibration statistics.
2. **Concurrency Safety**: From Observation 3, spawning a background worker thread that reads mutable UI state (`self.current_sentence_idx`) without freezing or disabling navigation buttons introduces a classic data race. Any user who clicks "Next Sentence" while the spinner says "Processing..." causes `compute_diff` to mismatch the sentence audio against the subsequent item.
3. **Contract Completeness**: From Observation 4, `PROJECT.md` defined the `compute_diff` interface contract for both `ui/voice_training_dialog.py` and `studio_server.py`. Leaving `studio_server.py` with the legacy un-stripped SequenceMatcher violates project architecture and creates a behavior divergence between native UI and web companion.
4. **Keyword Detection Accuracy**: From Observation 5, substring matching using Python's `in` operator without token or word boundary checks (`\b`) results in false negatives where incomplete or erroneous speech is accepted as containing the keyword (e.g. `"catch"` satisfying `"cat"`, `"main"` satisfying `"in"`).
5. **Conclusion Derivation**: The code implements the core algorithms genuinely and performs well, but the presence of three major flaws (dataset defect in #87, UI thread race condition, and unpatched duplicate diff in `studio_server.py`) necessitates a `REQUEST_CHANGES` verdict.

---

## 3. Findings

### [Major] Finding 1: Sentence #87 Phonetic Keyword Inconsistency
- **Where**: `data/calibration_sentences.json`, line 849.
- **What**: Phonetic keyword `"client demo"` does not appear in sentence text `"Client ko demo dikhane se pehle edge cases thoroughly test kar lena."`.
- **Why**: Guaranteed false positive `missing_keywords` whenever sentence #87 is read aloud.
- **Suggestion**: Update `"client demo"` to either `"demo"` or `"client"` or change sentence text to `"Client demo dikhane se pehle..."`.

### [Major] Finding 2: VoiceTrainingDialog Sentence Index Race Condition
- **Where**: `ui/voice_training_dialog.py`, lines 424-436.
- **What**: `self.current_sentence_idx` is read dynamically in `transcribe()` after transcription completes, but `next_sentence_btn` and `category_combo` are not disabled during recording/processing.
- **Why**: User advancing sentence during transcription causes the audio of sentence N to be diffed against sentence N+1.
- **Suggestion**: Freeze target text and keywords before launching thread:
  ```python
  target_item = dict(self.filtered_dataset[self.current_sentence_idx])
  target_text = target_item.get("text", "")
  keywords = list(target_item.get("phonetic_keywords", []))
  ```
  Pass them directly into the closure or worker thread, and disable navigation buttons during processing.

### [Major] Finding 3: Interface Contract Divergence in `studio_server.py`
- **Where**: `studio_server.py`, lines 75-130.
- **What**: `studio_server.py` still contains duplicate unpatched `compute_diff` code that leaks trailing punctuation into `misheard_pairs`.
- **Why**: Fails interface contract in `PROJECT.md`; web companion generates corrupt replacement rules.
- **Suggestion**: Remove duplicate `compute_diff` in `studio_server.py` and import from `calibration_engine`:
  ```python
  from calibration_engine import compute_diff, auto_register_misheard_pairs
  ```

### [Minor] Finding 4: Substring False-Negative in `missing_keywords`
- **Where**: `calibration_engine.py`, line 146.
- **What**: `kw_norm in clean_transcript` does plain substring search instead of whole-word or token-boundary matching.
- **Why**: Spoken word containing keyword as substring (e.g. "catch" for "cat") falsely counts as finding the keyword.
- **Suggestion**: Use word boundaries: `re.search(r'(?<!\w)' + re.escape(kw_norm) + r'(?!\w)', clean_transcript)`.

### [Minor] Finding 5: Incomplete Verification Command in Worker Handoff
- **Where**: `worker_m1_1/handoff.md`, lines 57-59.
- **What**: Verification command assumes `"cooper nets,"` is already in `voice_profile.json`.
- **Why**: Throws `AssertionError` when run as documented.
- **Suggestion**: Provide self-contained command that seeds the key:
  ```powershell
  .\.venv\Scripts\python.exe -c "from voice_profile import VoiceProfileManager; mgr = VoiceProfileManager.get_instance(); mgr.profile['word_replacements']['cooper nets,'] = 'Kubernetes'; assert mgr.apply_replacements('I manage cooper nets, in cloud') == 'I manage Kubernetes in cloud'; print('Regex verified!')"
  ```

---

## 4. Caveats

- Audio device recording in `VoiceTrainingDialog` was tested headlessly using synthetic NumPy arrays and mocked audio streams; physical microphone input was not tested with hardware.
- Test failures in `test_desktop_lifecycle.py` and `test_ui_responsiveness.py` were inspected and confirmed to belong to Milestone 3 scope (`FloatingWidget` signature and single-instance mutex hoisting).

---

## 5. Conclusion

**Verdict: REQUEST_CHANGES**

Worker M1 has delivered high-quality, authentic foundational code:
- `calibration_engine.py` is pure, lightweight, and has zero heavy imports.
- `voice_profile.py` lookaround regex correctly handles trailing punctuation keys like `"cooper nets,"`.
- `ui/voice_training_dialog.py` loads 100 bilingual sentences with ~22-43ms opening latency (<50ms requirement).
- No integrity violations or facades were found.

However, the worker must resolve:
1. Keyword mismatch in Sentence #87 (`data/calibration_sentences.json`).
2. Async sentence index closure race condition in `ui/voice_training_dialog.py`.
3. Legacy duplicate `compute_diff` in `studio_server.py`.

---

## 6. Verification Method

To verify resolution of these findings:

1. **Verify Sentence #87 Keyword Alignment**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import json, calibration_engine; d = json.load(open('data/calibration_sentences.json', encoding='utf-8'))[86]; norm_text = ' '.join(calibration_engine.clean_token(t) for t in d['text'].split()); assert all(' '.join(calibration_engine.clean_token(t) for t in kw.split()) in norm_text for kw in d['phonetic_keywords']), 'Keywords must match text!'; print('Sentence 87 keywords verified!')"
   ```

2. **Verify `studio_server.py` Uses `calibration_engine`**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import studio_server; assert hasattr(studio_server, 'compute_diff'); import calibration_engine; assert studio_server.compute_diff == calibration_engine.compute_diff, 'studio_server must import compute_diff from calibration_engine'; print('Contract verified!')"
   ```

3. **Verify All Calibration Unit Tests Pass**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest tests/test_speech_calibration.py
   .\.venv\Scripts\python.exe -m unittest tests/test_m1_challenger2_stress.py
   ```
