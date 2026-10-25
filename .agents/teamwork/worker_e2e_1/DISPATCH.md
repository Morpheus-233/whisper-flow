# E2E Test Writer Dispatch

**Role**: E2E Testing Track Specialist (`teamwork_preview_test_writer`)
**Working Directory**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_e2e_1`
**Authoritative User Request**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md` (specifically see ## 2026-10-22T09:54:41Z)
**Project Plan**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\PROJECT.md`

### Task
Design and implement the E2E Testing Infrastructure and test cases for Round 2:
1. Create `TEST_INFRA.md` at project root using the standard template (Category-Partition, BVA, Pairwise, Real-World Workload).
2. Create `benchmark_hinglish.py` at project root:
   - Contains 20 authoritative spoken Hindi/Hinglish benchmark test cases.
   - Verifies that Hindi/Hinglish inputs produce natural Romanized Hinglish (Latin alphabet) rather than literal English translations or Devanagari script.
   - Verifies technical English words ("deploy", "server", "github", "commit") remain in clean English.
   - Verifies Casual Chat style strips trailing periods/commas while keeping Hinglish text natural.
   - Verifies personal dictionary words appear with 100% fidelity.
   - Verifies latency metrics.
   - Runnable via `.venv\Scripts\python.exe benchmark_hinglish.py`.
3. Create new unit/integration tests in `tests/` covering:
   - `tests/test_two_stage_pipeline.py`: Stage 1 acoustic capture & Stage 2 Romanizer prompt / local fast Romanizer.
   - `tests/test_phonetic_calibration.py`: 1-click confirmation chips, Heard -> Target mapping, dual injection into Stage 1 & Stage 2.
   - `tests/test_settings_ui_r2.py`: Engine Selector toggle (Groq Cloud vs Local CPU int8), live Test Mic & API Connection button, style cards, floating dock live badges.
4. Ensure all existing 97 tests in `tests/` continue to be discoverable and pass via `.venv\Scripts\python.exe -m unittest discover tests`.
5. Once complete, publish `TEST_READY.md` at project root with runner command and coverage summary.

Report back in `handoff.md`.


## 2026-10-22T10:08:58Z
You are the E2E Test Writer for Whisper Flow Round 2.
Your working directory is: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_e2e_1
Authoritative user request: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md (specifically see ## 2026-10-22T09:54:41Z).
Project architecture: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
1. Create `TEST_INFRA.md` at project root based on the template in PROJECT.md:
   - Category-Partition, Boundary Value Analysis, Pairwise Combinatorial, Real-World Workloads.
   - Requirement-driven, opaque-box testing.
2. Create `benchmark_hinglish.py` at the project root:
   - Provide an automated benchmark containing 20 distinct, natural spoken Hindi/Hinglish test cases (conversational, tech/developer sentences, daily life, professional).
   - Test cases must verify:
     a) Hindi input produces natural Romanized Hinglish text in the Latin alphabet rather than literal English translation or Devanagari script.
     b) Technical English words ("deploy", "server", "github", "commit", "PR", "database", "python") remain in clean English.
     c) Saved personal dictionary words appear with 100% fidelity.
     d) Casual Chat style strips trailing periods and commas while keeping Hinglish text natural.
     e) End-to-end latency budget assertions (<350ms on Groq, <200ms on CPU).
   - The script should be runnable via `.venv\Scripts\python.exe benchmark_hinglish.py` and output a structured benchmark report with pass/fail metrics.
3. Design and add new comprehensive unit and integration tests into `tests/`:
   - `tests/test_hinglish_pipeline.py`: Unit tests for Stage 1 acoustic capture (Groq & local CPU int8), Stage 2 Romanizer prompt & local fast Romanizer, and style transforms.
   - `tests/test_calibration_phonetic_memory.py`: Unit tests for 1-click confirmation chips, Heard -> Target mapping registration, and dual injection.
   - `tests/test_settings_ui_r2.py`: Unit tests for Engine Selector toggle, live Test Mic & API Connection diagnostics, style cards, and floating dock live badges.
4. Ensure all existing 97 tests in `tests/` continue to pass without regression.
5. Create `TEST_READY.md` at project root with full runner instructions and coverage summary.

Write progress in progress.md, detailed report in handoff.md, and notify when complete via send_message.
