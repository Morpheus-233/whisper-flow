# Dispatch: E2E Test Writer (Dual Track)

**Role**: E2E Test Suite Architect
**Type**: teamwork_preview_test_writer
**Working Directory**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\test_writer_e2e_1
**Project Root**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
**Original Request**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md
**Project Scope Document**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md

## Exclusive Write Ownership
You exclusively own: `tests/` directory (e.g. `tests/__init__.py`, `tests/test_speech_calibration.py`, `tests/test_style_engine.py`, `tests/test_desktop_lifecycle.py`, `tests/test_ui_responsiveness.py`, `tests/test_whisper_engine.py`).
You MUST NOT modify files outside `tests/`.

## Objectives
1. Read ORIGINAL_REQUEST.md and PROJECT.md carefully.
2. Build a comprehensive opaque-box test suite under `tests/` discoverable and runnable via `.\.venv\Scripts\python.exe -m unittest discover tests`.
3. Design tests covering the 4 Tiers:
   - Tier 1: Feature Coverage (Bilingual sentences dataset 100 sentences, SequenceMatcher accuracy diffing, automated phonetic correction, initial_prompt biasing, CPU int8 engine settings, Casual chat format, Developer Mode, Custom Persona, single-instance mutex check, AllowSetForegroundWindow, dialog presentation, dark title bar, 1-click dictionary removal, search filtering).
   - Tier 2: Boundary & Corner Cases (empty transcripts, punctuation-laden keys like "cooper nets,", zero-match speech, extreme lengths, invalid audio, secondary process fast-exit under 100ms benchmark).
   - Tier 3: Cross-Feature Combinations (phonetic replacements + casual styling, custom dictionary biasing + Hinglish speech, developer mode syntax + voice profile).
   - Tier 4: Real-world Workload Scenarios (simulating dictation workflows, calibration session leading to active transcription replacement).
4. Ensure tests are self-contained, mocking audio device I/O where appropriate so tests run reliably on headless or CI environments without physical audio hardware.
5. Create `TEST_READY.md` at `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\TEST_READY.md` summarizing the test suite runner command, tier breakdown, and feature coverage checklist.
6. Verify test suite execution using `.\.venv\Scripts\python.exe -m unittest discover tests`.
7. Write handoff report to `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\test_writer_e2e_1\handoff.md`.
8. Send completion message to orchestrator.


## 2026-10-15T14:59:46Z
From: 594ef618-48c0-4063-b24e-931d4cc7a88e
You are E2E Test Suite Architect.
Your working directory is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\test_writer_e2e_1
The project root is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
Read C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md, C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md, and your dispatch at C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\test_writer_e2e_1\DISPATCH.md before starting.
You exclusively own the tests/ directory.
Implement a comprehensive, modular test suite under tests/ discoverable and passing via .\.venv\Scripts\python.exe -m unittest discover tests.
Cover Tiers 1-4 across bilingual speech calibration, zero-GPU engine, style transformations, and desktop lifecycle.
Publish TEST_READY.md at C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\TEST_READY.md.
Run the test suite and write handoff.md in your working directory. Notify orchestrator via send_message when complete.
