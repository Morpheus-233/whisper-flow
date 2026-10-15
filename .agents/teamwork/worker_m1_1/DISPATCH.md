# Dispatch: Worker M1 (Bilingual Calibration & Phonetic Mapper)

**Role**: Bilingual Calibration & Phonetic Mapper Worker
**Type**: teamwork_preview_worker
**Working Directory**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_1
**Project Root**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
**Original Request**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md
**Project Scope Document**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md

## Exclusive Write Ownership
You exclusively own:
- `calibration_engine.py` (new standalone module)
- `voice_profile.py`
- `ui/voice_training_dialog.py`
- `data/calibration_sentences.json`
You MUST NOT modify files outside your ownership scope.

## Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Objectives
1. Read ORIGINAL_REQUEST.md and PROJECT.md carefully.
2. Review Survey Explorer 1 and Explorer 2 handoffs:
   - `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_1\handoff.md`
   - `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_2\handoff.md`
3. Implement `calibration_engine.py`:
   - Standalone, zero-side-effect diffing module.
   - `compute_diff(target_text, transcribed_text, phonetic_keywords=None)`:
     - Normalizes tokens, matches sequences via `difflib.SequenceMatcher`.
     - Clamps accuracy to `0.0` - `100.0`.
     - Extracts `misheard_pairs` with punctuation cleanly stripped (e.g. `"hoon"` not `"hoon."`).
   - `load_calibration_dataset()`: Loads all 100 sentences (50 English, 50 Hindi/Hinglish) from `data/calibration_sentences.json`.
   - `auto_register_misheard_pairs(misheard_pairs, profile_mgr)`: Registers clean target replacements into `voice_profile.json` automatically.
4. Update `voice_profile.py`:
   - Fix `apply_replacements` regex to use conditional lookarounds `(?<!\w)` and `(?!\w)` so keys with punctuation like `"cooper nets,"` match and replace cleanly.
   - Ensure `get_initial_prompt` handles custom words and truncates safely for Whisper's token window.
5. Update `ui/voice_training_dialog.py`:
   - Load the 100 bilingual calibration sentences from `data/calibration_sentences.json` via `calibration_engine.load_calibration_dataset()` instead of the 3 hardcoded sentences.
   - Run diffing using `calibration_engine.compute_diff` and enable automated registration of misheard words into `voice_profile.json`.
6. Run unit tests and verification commands using `.\.venv\Scripts\python.exe`.
7. Write handoff report to `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_1\handoff.md`.
8. Send completion message to orchestrator.


## 2026-10-15T14:59:46Z
From: 594ef618-48c0-4063-b24e-931d4cc7a88e
You are Worker M1 (Bilingual Calibration & Phonetic Mapper).
Your working directory is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_1
The project root is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
Read C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md, C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md, and your dispatch at C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_1\DISPATCH.md before starting.
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
You exclusively own calibration_engine.py, voice_profile.py, ui/voice_training_dialog.py, and data/calibration_sentences.json.
Implement calibration_engine.py with SequenceMatcher diffing (punctuation-clean misheard pairs), load 100 sentences in VoiceTrainingDialog, auto-register phonetic pairs, and fix lookaround regex boundaries in voice_profile.py.
Run tests and write handoff.md in your working directory. Notify orchestrator via send_message when complete.
