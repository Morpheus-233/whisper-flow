# BRIEFING — 2026-10-22T10:20:00Z

## Mission
Implement two-stage Hinglish speech transcription and styling pipeline in Whisper Flow: Stage 1 acoustic capture with anti-translation and resilient Groq/CPU failover in `whisper_engine.py`, Stage 2 fast Romanizer with anti-translation prompt and sub-0.01ms CPU Romanizer in `style_engine.py`, structured context and deterministic 100% dictionary post-pass in `voice_profile.py`, config updates in `config.py` and `config.json`, and text cleaner verification in `text_cleaner.py`.

## 🔒 My Identity
- Archetype: teamwork_preview_worker
- Roles: implementer, qa, specialist
- Working directory: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_1
- Original parent: 594ef618-48c0-4063-b24e-931d4cc7a88e
- Milestone: M1 (Bilingual Calibration & Phonetic Mapper)
- Round 2 Parent: b7127cef-b446-4dca-a8e7-b0da25424e7e
- Round 2 Milestone: M1 (Two-Stage Hinglish Pipeline Worker)

## 🔒 Key Constraints
- Exclusively own: calibration_engine.py, voice_profile.py, ui/voice_training_dialog.py, data/calibration_sentences.json.
- MUST NOT modify files outside exclusive ownership scope.
- Pure diffing in calibration_engine.py: zero heavy dependencies (no PySide6 or faster-whisper imports).
- SequenceMatcher diffing with punctuation-clean misheard pairs and clamped accuracy (0.0 to 100.0).
- Regex lookaround boundaries `(?<!\w)` and `(?!\w)` in voice_profile.py.
- Auto-register clean phonetic pairs into voice_profile.json.
- Load all 100 bilingual sentences in VoiceTrainingDialog.
- DO NOT CHEAT: genuine implementations only, no dummy facades or hardcoded values.
- Round 2 Exclusive write ownership: config.py, config.json, whisper_engine.py, style_engine.py, text_cleaner.py, voice_profile.py.
- Round 2 Integrity Mandate: No hardcoding test results, no dummy facades, genuine implementations only.
- Groq /audio/transcriptions endpoint only, 5s timeout, User-Agent: WhisperFlow.
- Local CPU base int8 failover on missing key, 401, 429, timeout, or local engine_mode.
- Model name sanitization: replace any .en suffix with base.
- Anti-translation prompt for llama-3.3-70b-versatile.
- Pure Python FastDevanagariRomanizer with 200+ word dictionary + transliterator with schwa deletion (<0.01ms, 0 GPU VRAM).
- Deterministic 100% dictionary match guarantee in voice_profile.py via regex post-pass.

## Current Parent
- Conversation ID: b7127cef-b446-4dca-a8e7-b0da25424e7e
- Updated: 2026-10-22T10:20:00Z

## Task Summary
- **What to build**: Two-stage speech transcription and styling pipeline: config updates, `transcribe_stage1` and 3-stage coordination in `whisper_engine.py`, `format_two_stage` with Groq Cloud prompt and local `FastDevanagariRomanizer` in `style_engine.py`, `get_stage2_context` and 100% dictionary guarantee in `voice_profile.py`, and `text_cleaner.py` verification.
- **Success criteria**: All unittests pass, Devanagari is Romanized to Latin Hinglish, no English translation of Hindi speech, technical words preserved, 100% dictionary match, sub-350ms cloud latency, zero-crash CPU fallback.
- **Interface contracts**: PROJECT.md lines 69-77, 85-88.
- **Code layout**: config.py, config.json, whisper_engine.py, style_engine.py, text_cleaner.py, voice_profile.py.

## Key Decisions Made
- [Round 2] Update `config.py` and `config.json` with `"engine_mode": "groq"`, `"language_mode": "hinglish"`, and default model `"base"`.
- [Round 2] Implement `transcribe_stage1` in `whisper_engine.py` with Groq `/audio/transcriptions`, 5.0s timeout, User-Agent `WhisperFlow`, auto language detection, and automatic CPU int8 fallback.
- [Round 2] Implement `FastDevanagariRomanizer` (200+ dictionary + transliterator with schwa deletion) and `format_two_stage` in `style_engine.py`.
- [Round 2] Implement `get_stage2_context`, enhanced `get_initial_prompt`, and enhanced `apply_replacements` with custom_words casing normalization in `voice_profile.py`.

## Artifact Index
- DISPATCH.md — Assignment instructions
- BRIEFING.md — Situational awareness
- progress.md — Liveness heartbeat and status tracker
- handoff.md — Final self-contained handoff report

## Change Tracker
- **Files modified**:
  - `config.py`: Added `"engine_mode": "groq"` and `"language_mode": "hinglish"` to `DEFAULT_CONFIG`.
  - `config.json`: Updated `"model_name": "base"`, `"engine_mode": "groq"`, `"language_mode": "hinglish"`.
  - `whisper_engine.py`: Model sanitization (.en -> base), `transcribe_stage1` with Groq 5s timeout, User-Agent `WhisperFlow`, local CPU int8 failover, and 3-stage coordination in `transcribe()`.
  - `style_engine.py`: `FastDevanagariRomanizer` with 220+ word dictionary, DIGITS transliteration, schwa deletion, `format_two_stage` with Llama-3.3-70b prompt, 401 circuit breaker, and style enforcement.
  - `voice_profile.py`: `get_stage2_context` XML blocks, 800-char bounded `get_initial_prompt` with replacement targets, and deterministic 100% dictionary regex post-pass in `apply_replacements`.
  - `text_cleaner.py`: Verified `format_casual_chat` preserves Hinglish while cleaning formal trailing punctuation.
- **Build status**: PASS (161/161 unit tests, 20/20 benchmark cases)
- **Pending issues**: None

## Quality Status
- **Build/test result**: 161/161 unit tests passed in 3.278s (`discover tests`). 42/42 targeted M1 tests passed in 0.142s (`test_whisper_engine.py`, `test_style_engine.py`, `test_hinglish_pipeline.py`).
- **Benchmark result**: 20/20 Hinglish test cases passed in 6.53ms mean CPU latency (<200ms budget, 0 MB GPU VRAM).
- **Lint status**: Clean; no new warnings or syntax errors.
- **Tests added/modified**: Verified all suites in `tests/`.

## Loaded Skills
- None
