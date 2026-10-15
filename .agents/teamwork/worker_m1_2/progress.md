# Progress: Worker M1 (Remediation)

- Last visited: 2026-10-15T15:35:00Z
- Status: Complete
- Active Task: Ready for final handoff.
- Completed Steps:
  1. Fix Sentence #87 keyword in `data/calibration_sentences.json` ("client demo" -> "demo").
  2. Snapshot `target_item` and lock navigation controls during recording and transcription in `ui/voice_training_dialog.py`.
  3. Harden `calibration_engine.py` and `voice_profile.py` for Devanagari combining marks (matras), pure punctuation diffs, and word-boundary keyword matching.
  4. Deduplicate `compute_diff` in `studio_server.py` by importing from `calibration_engine`.
  5. Run all 82 tests via `python -m unittest discover tests` — all passed (0 failures, 0 errors).
