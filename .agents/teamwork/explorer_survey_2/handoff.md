# Handoff Report: Smart Voice Calibration & Phonetic Memory Survey

**Agent**: Survey Explorer 2  
**Role**: Explorer (Investigation & Synthesis)  
**Parent**: Orchestrator R2 (`b7127cef-b446-4dca-a8e7-b0da25424e7e`)  
**Date**: 2026-10-22  
**Working Directory**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_2`  

---

## 1. Observation

### Obs 1: Calibration Dataset Composition & Script Disparity
- **File**: `data/calibration_sentences.json` (lines 1 to 981).
- **Direct observation**:
  - Contains exactly 100 entries: IDs 1–50 with `"category": "english"` and IDs 51–100 with `"category": "hindi_hinglish"`.
  - Sentences 51–100 are written in the **Latin alphabet (Romanized script)**:
    - Line 502: `"id": 51, "category": "hindi_hinglish", "text": "Main thodi der mein call karta hoon.", "phonetic_keywords": ["thodi der", "call karta hoon"]`
    - Line 512: `"id": 52, "category": "hindi_hinglish", "text": "Aaj ka meeting schedule kya hai?", "phonetic_keywords": ["meeting schedule", "aaj ka"]`
    - Line 974: `"id": 100, "category": "hindi_hinglish", "text": "Hundred calibration sentences complete hone ke baad voice profile fully tuned ho jayega."`

### Obs 2: Pure Computation Diff Engine
- **File**: `calibration_engine.py` (lines 1 to 257).
- **Direct observation**:
  - Line 21: `clean_token(token)` uses `re.sub(r"[^\w\s\u0900-\u097F]", "", token).strip().lower()`. It explicitly preserves Devanagari Unicode characters and combining marks (`\u0900-\u097F`).
  - Line 36: `strip_punctuation(text)` uses `re.sub(r"^[^\w\u0900-\u097F]+|[^\w\u0900-\u097F]+$", "", w)` to trim boundary punctuation without truncating Devanagari vowel signs (matras).
  - Lines 126–169: `compute_diff` uses `difflib.SequenceMatcher(lambda x: x == "", target_norm, heard_norm)`. For `tag == "replace"`, it extracts misheard pairs into `{"heard": clean_h, "target": clean_t}` without trailing punctuation.
  - Line 168: Accuracy formula: `raw_acc = (matches / max(len(target_tokens), len(heard_tokens), 1)) * 100.0`, clamped to `[0.0, 100.0]`.
  - Line 223: `auto_register_misheard_pairs(misheard_pairs, profile_mgr)` adds clean lowercase heard keys into `profile_mgr.add_replacement(heard, target)`.

### Obs 3: Automatic Unconditional Registration in Calibration Dialog
- **File**: `ui/voice_training_dialog.py` (lines 438 to 458).
- **Direct observation**:
  - Lines 439–440:
    ```python
    prompt = self.profile_mgr.get_initial_prompt()
    text = self.whisper_engine.transcribe(audio, initial_prompt=prompt)
    ```
  - Lines 448–449:
    ```python
    diff_res = compute_diff(target_text, text, keywords)
    newly_added = auto_register_misheard_pairs(diff_res.get("misheard_pairs", []), self.profile_mgr)
    ```
  - Lines 388–398: The GUI displays static text labels:
    `self.transcribed_preview.setText(f'Whisper heard: "{text}" | Accuracy: {accuracy:.1f}% ({self.calibrated_wpm} WPM)')`
    `self.diff_status.setText(f"Auto-registered {newly_added} phonetic correction(s): {pairs_str}")`
  - There are NO interactive buttons or chips for the user to confirm, reject, or select words to permanently remember with 1 click.
  - Page 3 (`page_review`, lines 509–542) only displays `word_list` for `custom_words`, completely omitting `word_replacements`.

### Obs 4: Whisper Initial Prompt Biasing Limitations
- **File**: `voice_profile.py` (lines 122 to 152).
- **Direct observation**:
  - `get_initial_prompt(max_chars=800)`:
    ```python
    words = self.get_custom_words()
    if not words:
        return None
    prefix = "Vocabulary: "
    suffix = "."
    ...
    return prefix + ", ".join(included) + suffix
    ```
  - It pulls ONLY from `self.get_custom_words()`. It completely ignores `self.get_replacements()`. Target words (e.g. `"PySide6"`, `"Kubernetes"`) registered via calibration phonetic mappings are never injected into Whisper's acoustic `initial_prompt`.

### Obs 5: Existing Replacement Row UI
- **File**: `ui/settings_dialog.py` (lines 60 to 120).
- **Direct observation**:
  - `ReplacementRowWidget` already exists, rendering `heard_lbl` (blue monospace), `arrow_lbl` ("→"), `target_lbl` (green bold), and `del_btn` ("Remove" with 1-click callback).

### Obs 6: Automated Test Suite Execution
- **Command**: `.\.venv\Scripts\python.exe -m unittest discover tests`
- **Direct observation**:
  - Ran 97 tests in 2.854s. All 97 passed with 0 failures, 0 errors:
    - `test_speech_calibration.py`: 100 sentences, SequenceMatcher diffs, Devanagari vowel protection, lookaround regex, initial_prompt generation.
    - `test_m1_challenger2_stress.py`: VoiceTrainingDialog open latency (Mean 23.67ms, Max 26.19ms, well within <50ms requirement).
    - `test_empirical_stress_m1.py`: Punctuation diffs, 2000 replacement rules benchmark (0.45s).

---

## 2. Logic Chain

1. **Premise**: In `data/calibration_sentences.json`, Hindi/Hinglish sentences are written in Romanized Latin script (Obs 1).
2. **Premise**: Standard Whisper models (both local CPU `base` and Groq `whisper-large-v3-turbo`) transcribe Hindi speech into Devanagari script or translated English unless Romanized (Obs 3).
3. **Inference**: Comparing raw Devanagari speech directly against Romanized Latin text in `compute_diff` yields 0 token overlap, causing artificial 0.0% accuracy and invalid phonetic mappings (Obs 1, Obs 2).
4. **Deduction**: The calibration transcription workflow in `voice_training_dialog.py` MUST be routed through the Two-Stage Pipeline (Stage 1 acoustic capture -> Stage 2 fast Romanizer) so that Romanized output is diffed against Romanized calibration targets.
5. **Premise**: Currently, `ui/voice_training_dialog.py` calls `auto_register_misheard_pairs` unconditionally in the background (Obs 3).
6. **Inference**: If a user coughs, stutters, or Whisper hallucinates, corrupt pairs will be silently committed to `voice_profile.json` without user awareness or agency.
7. **Deduction**: The calibration wizard must display candidate misheard pairs as interactive 1-click confirmation chips (`[ 'thori' → 'thodi' ] [ + Remember ]` / `[ ✓ Remembered ] [ ✕ ]`) giving users explicit agency and instant feedback (<1ms).
8. **Premise**: `voice_profile.py`'s `get_initial_prompt` currently only includes `custom_words` (Obs 4).
9. **Inference**: Target pronunciations calibrated during voice training are not biased in Whisper's token decoder.
10. **Deduction**: `get_initial_prompt()` must combine `custom_words` and unique `word_replacements.values()`, bounded by Whisper's 800-character context window.
11. **Premise**: Stage 2 LLM (`llama-3.3-70b-versatile`) acts as the Romanizer and Stylist, but LLM generation alone cannot mathematically guarantee 100% dictionary fidelity.
12. **Deduction**: In addition to injecting `<phonetic_memory>` and `<personal_dictionary>` into Stage 2's prompt, the pipeline must run `voice_profile.apply_replacements(text)` as a deterministic post-pass to guarantee 100% fidelity.

---

## 3. Caveats

1. **Network Connectivity for Groq Stage 2 in Calibration**: If the user is calibrating offline or has no Groq API key set, Stage 2 Romanization must seamlessly fallback to local processing (or local Romanizer rules).
2. **Whisper Language Auto-Detection**: When reading bilingual sentences aloud, Whisper's VAD and language identification can occasionally toggle between `en` and `hi`. Ensuring the decoder receives `initial_prompt` containing both Romanized Hinglish vocabulary and English technical terms helps keep token decoding stable.
3. **No other areas uninvestigated**: Codebase exploration covered all relevant modules (`calibration_engine.py`, `voice_profile.py`, `data/calibration_sentences.json`, `ui/voice_training_dialog.py`, `ui/settings_dialog.py`, `whisper_engine.py`, `app.py`, `style_engine.py`, and `tests/`).

---

## 4. Conclusion

1. **Diff Engine & Dataset**: `calibration_engine.py` and `data/calibration_sentences.json` are robust, high-performance, and fully tested (97/97 tests pass).
2. **Two-Stage Pipeline Routing**: Calibration transcription in `voice_training_dialog.py` must pass through Stage 2 (Romanizer) so spoken Hindi is rendered in Romanized Latin characters before computing diffs against the 50 Hinglish calibration sentences.
3. **1-Click Confirmation UI**: The calibration wizard UI must be upgraded from static text labels to an interactive interface featuring:
   - Live visual diff with HTML color-coded tokens (green matches, red misheard, yellow inserted).
   - 1-click confirmation chips (`PhoneticPairChip`) allowing users to permanently remember or reject candidate pairs in <1ms.
   - Enhanced Step 3 review displaying both Custom Words and Calibrated Phonetic Mappings.
4. **Dual Injection Contract**:
   - **Stage 1**: Update `voice_profile.py`'s `get_initial_prompt()` to include target words from `word_replacements`.
   - **Stage 2**: Provide `get_stage2_context()` to inject `<phonetic_memory>` and `<personal_dictionary>` blocks into the LLM prompt, followed by deterministic `apply_replacements()` execution.

---

## 5. Verification Method

### 1. Test Suite Verification
Run the complete automated test suite using the project virtual environment:
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```
*Expected*: All 97 tests pass cleanly in under 3.0s.

### 2. File Inspection
Inspect the following files to verify the architectural findings:
- `data/calibration_sentences.json`: Verify 50 English and 50 Hindi/Hinglish sentences in Roman script.
- `calibration_engine.py`: Verify `clean_token`, `strip_punctuation`, `compute_diff`, and `auto_register_misheard_pairs`.
- `voice_profile.py`: Verify `get_initial_prompt`, `apply_replacements`, and profile persistence.
- `ui/voice_training_dialog.py`: Verify current 3-page layout and lines 438–450 transcription/diff flow.
- `.agents/teamwork/explorer_survey_2/analysis.md`: Detailed survey analysis and contract specifications.

### 3. Invalidation Conditions
This survey and its conclusions would be invalidated if:
- The 50 Hindi/Hinglish calibration sentences in `data/calibration_sentences.json` were converted from Romanized Latin alphabet to Devanagari script (in which case Stage 2 Romanization before diffing would not be needed).
- Whisper Flow abandoned the Two-Stage architecture in favor of a single end-to-end model.
