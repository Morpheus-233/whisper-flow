# Execution Plan: Whisper Flow Round 2 Finalization (Gen 2)

## Goal
Complete Milestone M3, verify and pass M3 Gate, execute Milestone M4 (Final E2E Pass, Stress Verification, Acceptance Criteria Audit), and deliver Victory Report.

## Phase 1: Milestone M3 Finalization & Gate Closure
1. **Dispatch Worker (`worker_m3_fix`)**:
   - Apply Challenger M3's exact fix: Remove line 445 `QTimer.singleShot(0, self._ensure_dictionary_loaded)` from `ui/settings_dialog.py`.
   - Ensure deferred loading on Tab 2 (`Personal Dictionary`) is strictly preserved.
   - Run tests:
     - `.\.venv\Scripts\python.exe -m unittest -v tests/test_m3_empirical_challenger.py`
     - `.\.venv\Scripts\python.exe -m unittest -v tests/test_settings_ui_r2.py`
     - `.\.venv\Scripts\python.exe -m unittest discover tests`
     - `.\.venv\Scripts\python.exe benchmark_hinglish.py`
   - Produce handoff report.
2. **Dispatch Challenger (`challenger_m3_recheck`)**:
   - Independently run `tests/test_m3_empirical_challenger.py` and verify all 15 stress tests pass with sub-50ms presentation latency.
   - Deliver verdict.
3. **Close M3 Gate**:
   - Update `GATE_STATUS.md` with Worker, Reviewer (already APPROVE), Auditor (already CLEAN), and Challenger verdicts.
   - Mark Milestone M3 DONE in `PROJECT.md` and `progress.md`.

## Phase 2: Milestone M4 (Final E2E Pass, Stress Verification & Victory Report)
1. **Dispatch M4 Verification Worker (`worker_m4_e2e`)**:
   - Run full discoverable test suite across all 237+ tests.
   - Run `benchmark_hinglish.py` across all 20 test cases.
   - Verify all 8 Acceptance Criteria from `ORIGINAL_REQUEST.md`:
     1. Natural Romanized Hinglish text without literal translation or Devanagari.
     2. Technical English words in Hinglish sentences remain clean English.
     3. Saved personal dictionary words appear with 100% fidelity.
     4. Casual Chat style strips trailing punctuation.
     5. Sub-350ms end-to-end latency budget on Groq Cloud and sub-200ms on CPU.
     6. Preferences panel exposes engine toggle with working Test Connection button.
     7. Floating dock reflects active engine and language status badges.
     8. All automated tests pass cleanly.
   - Produce comprehensive E2E verification report.
2. **Dispatch Challenger / Stress Verifier (`challenger_m4_stress`)**:
   - Execute adversarial edge cases, concurrent signals, and latency stress checks.
3. **Dispatch Forensic Auditor (`auditor_m4_final`)**:
   - Complete integrity forensic audit on final codebase.
4. **Close M4 Gate**:
   - Update `GATE_STATUS.md`.
   - Mark M4 DONE in `PROJECT.md`.

## Phase 3: Victory Report & Human Reporting
1. Synthesize final results.
2. Write `handoff.md`.
3. Send structured victory report to caller parent agent via `send_message`.
