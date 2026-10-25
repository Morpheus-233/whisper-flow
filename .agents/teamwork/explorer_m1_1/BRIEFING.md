# BRIEFING — 2026-10-22T10:15:00Z

## Mission
Investigate Stage 1 Acoustic Capture in whisper_engine.py for Milestone M1 (Two-Stage Hinglish Pipeline), covering Groq Cloud (whisper-large-v3-turbo) and local CPU fallback, task="transcribe", language handling, output interface for Stage 2, and test plans.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_m1_1
- Original parent: b7127cef-b446-4dca-a8e7-b0da25424e7e
- Milestone: M1 (Two-Stage Hinglish Pipeline)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement in source files (only write reports and analysis in explorer_m1_1 directory)
- Never modify whisper-flow source code directly
- Strictly prevent Whisper from performing translation (must enforce transcribe task)
- Keep all agent metadata inside .agents/teamwork/explorer_m1_1

## Current Parent
- Conversation ID: b7127cef-b446-4dca-a8e7-b0da25424e7e
- Updated: 2026-10-22T10:15:00Z

## Investigation State
- **Explored paths**:
  - `whisper_engine.py` (WhisperEngine, load_model, _transcribe_groq, transcribe)
  - `config.py` & `config.json` (model_name defaults, groq_api_key, missing engine_mode/language_mode)
  - `style_engine.py` (StyleEngine, format_two_stage contract, prompts, Ollama fallback)
  - `voice_profile.py` (VoiceProfileManager, get_initial_prompt, apply_replacements)
  - `app.py` (AudioEngine -> WhisperEngine -> VoiceProfileManager -> StyleEngine)
  - `tests/test_whisper_engine.py` & test suite execution
  - Groq Whisper Audio Transcriptions API documentation & endpoints
  - Peer explorer dispatches (`explorer_m1_2`, `explorer_m1_3`)
- **Key findings**:
  1. Groq Cloud endpoint `https://api.groq.com/openai/v1/audio/transcriptions` guarantees transcription (separate from `/translations`).
  2. In `faster_whisper`, `model.transcribe()` must explicitly specify `task="transcribe"`, and `language=None` (or "auto") for automatic language detection to handle code-mixed Hinglish without forcing English or Devanagari prematurely.
  3. `config.json` currently had `"model_name": "base.en"`, which breaks multilingual/Hinglish transcription in local CPU mode. WhisperEngine must sanitize any `.en` suffix to `"base"`.
  4. Groq failover must check `engine_mode == "local"` to skip network attempts when user wants offline mode. On network error, timeout (5s), 401/429/503 HTTP errors, failover to local CPU int8 model is automatic and zero-crash.
  5. Decoupled `transcribe_stage1(...)` cleanly produces raw transcript for Stage 2 `format_two_stage(...)`.
- **Unexplored areas**: None for Stage 1. Stage 2 and dictionary guarantee are scoped to M1 Explorer 2 and M1 Explorer 3.

## Key Decisions Made
- Architected `transcribe_stage1` as dedicated Stage 1 acoustic capture method.
- Preserved `transcribe` as two-stage coordinator implementing `PROJECT.md` contract.
- Defined fallback strategy with 5-second timeout, `engine_mode` check, and automatic local CPU recovery.
- Designed 9 unit test cases targeting Stage 1 parameters, error modes, and interface boundaries.

## Artifact Index
- DISPATCH.md — incoming dispatch instructions
- BRIEFING.md — working memory and identity
- progress.md — liveness heartbeat
- analysis.md — detailed findings and blueprints
- handoff.md — 5-component handoff report
