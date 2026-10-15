# Dispatch: Worker M1 (Iteration 2 — Remediation)

**Role**: Bilingual Calibration Remediation Worker
**Type**: teamwork_preview_worker
**Working Directory**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_2
**Project Root**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
**Original Request**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md
**Project Scope Document**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md

## Exclusive Write Ownership
You exclusively own:
- `data/calibration_sentences.json`
- `ui/voice_training_dialog.py`
- `calibration_engine.py`
- `voice_profile.py`
- `studio_server.py`

## Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Remediation Objectives
Review the Gate reports from Reviewer 1, Reviewer 2, and Challenger 1:
- `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\reviewer_m1_1\handoff.md`
- `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\reviewer_m1_2\handoff.md`
- `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\challenger_m1_1\handoff.md`

Implement the following targeted fixes:
1. **Sentence #87 in `data/calibration_sentences.json`**:
   - Align the phonetic keywords with the sentence text so that `"client demo"` is replaced with `"demo"` (or update sentence text to `"Client demo dikhane se pehle edge cases thoroughly test kar lena."`), ensuring all phonetic keywords are exact substrings of their sentence text.
2. **`ui/voice_training_dialog.py` Thread Safety & UI Controls**:
   - Capture `target_item = self.filtered_dataset[self.current_sentence_idx]` locally before launching `threading.Thread(target=transcribe, daemon=True).start()`, so the thread uses an immutable snapshot.
   - In `_toggle_sentence_recording`: when recording stops and transcription starts, disable `self.next_sentence_btn`, `self.prev_sentence_btn`, and `self.category_combo`.
   - In `_on_speech_finished`: re-enable `self.next_sentence_btn`, `self.prev_sentence_btn`, and `self.category_combo`.
3. **`calibration_engine.py` & `voice_profile.py` Devanagari Unicode & Edge Cases**:
   - In `strip_punctuation(text)`: Do NOT strip Unicode combining marks (`Mn` and `Mc` categories, such as Devanagari vowel signs/matras `\u0900-\u097F`). Only strip punctuation characters (`P*`) and non-combining symbols.
   - In `clean_token(token)`: Preserve Devanagari characters and combining marks: `re.sub(r"[^\w\s\u0900-\u097F]", "", token).strip().lower()`.
   - In `compute_diff`: When both target and heard contain no alphanumeric or Devanagari tokens (e.g. `'...'` vs `'???'`), return `0.0%` accuracy unless exact raw strings match.
   - In `voice_profile.py:apply_replacements`: Ensure lookaround boundaries `(?<!\w)` and `(?!\w)` correctly handle Devanagari words ending in combining marks.
4. **`studio_server.py` Interface Contract Integration**:
   - In `studio_server.py`, import `compute_diff` from `calibration_engine` instead of having duplicate unpatched logic.
5. **Verification**:
   - Run full test suite: `.\.venv\Scripts\python.exe -m unittest discover tests`.
   - Verify all tests pass with 0 failures and 0 errors.
   - Write handoff report to `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_2\handoff.md`.
   - Send completion message to orchestrator.


## 2026-10-15T15:21:10Z
You are Worker M1 (Iteration 2 — Remediation).
Your working directory is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_2
The project root is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
Read C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md, C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md, and your dispatch at C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_2\DISPATCH.md before starting.
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
Implement the 4 required remediation items:
1. Fix Sentence #87 keyword in data/calibration_sentences.json.
2. Snapshot target_item and disable navigation controls in ui/voice_training_dialog.py.
3. Harden calibration_engine.py and voice_profile.py for Devanagari combining marks (matras) and pure-punctuation diffing.
4. Integrate compute_diff from calibration_engine into studio_server.py.
Run all tests via .\.venv\Scripts\python.exe -m unittest discover tests.
Write handoff.md in your working directory and notify the orchestrator when complete.
