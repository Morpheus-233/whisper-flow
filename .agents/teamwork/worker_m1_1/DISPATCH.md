# M1 Worker 1 Dispatch

**Role**: Implementation Worker (`teamwork_preview_worker`)
**Working Directory**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_1`
**Authoritative User Request**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md` (specifically see ## 2026-10-22T09:54:41Z)
**Project Plan**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\PROJECT.md`
**Explorer Findings**:
- Stage 1 Acoustic Capture: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_m1_1\handoff.md` and `analysis.md`
- Stage 2 Fast Romanizer & Stylist: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_m1_2\handoff.md` and `analysis.md`
- Dictionary Match & Latency Budget: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_m1_3\handoff.md` and `analysis.md`

### Exclusive Write Ownership:
- `config.py`
- `config.json`
- `whisper_engine.py`
- `style_engine.py`
- `text_cleaner.py`
- `voice_profile.py`

### Mandatory Integrity Warning:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Implementation Tasks:
1. **`config.py` & `config.json`**:
   - Add `"engine_mode": "groq"` (options: `"groq"`, `"local"`) and `"language_mode": "hinglish"` (options: `"hinglish"`, `"en"`) to `DEFAULT_CONFIG`.
   - Update `config.json` default model to `"base"` (strip `.en` suffix).
2. **`whisper_engine.py`**:
   - Implement `transcribe_stage1(audio_data, sample_rate=16000, initial_prompt=None, language=None, engine_mode=None) -> str`.
   - In Groq transcription, strictly target `/openai/v1/audio/transcriptions` with `task="transcribe"`. Omit `language` when auto or None; set User-Agent: `WhisperFlow`; set timeout to 5.0s.
   - In local `faster-whisper` CPU int8 transcription, explicitly pass `task="transcribe"` and `language=None` (or specified language).
   - Sanitize any model name ending in `.en` to `"base"`.
   - If `engine_mode == "local"`, bypass Groq completely. On any Groq API error (401, 429, timeout, offline), automatically fall back to local CPU int8 model with 0 MB GPU VRAM.
   - Wire `transcribe()` to coordinate Stage 1 (`transcribe_stage1`) -> Stage 2 (`StyleEngine.format_two_stage`) -> Stage 3 (`VoiceProfileManager.apply_replacements`).
3. **`style_engine.py`**:
   - Implement `format_two_stage(raw_text, style=None, voice_profile=None, engine_mode=None, groq_api_key=None) -> str`.
   - Groq Cloud: call `llama-3.3-70b-versatile` with the adversarial anti-translation system prompt that:
     * Transcribes Hindi to natural Romanized Hinglish (Latin alphabet).
     * Strictly prevents English translation (e.g. forbids "Main theek hoon" -> "I am fine").
     * Preserves English technical words and code tokens ("deploy", "server", "github", "commit", "PR").
     * Directly enforces active speech style (Casual Chat, Developer Mode, Professional, Custom Persona).
     * Injects `<personal_dictionary>` and `<phonetic_memory>`.
   - Local CPU Fallback: Implement `FastDevanagariRomanizer` with 2-tier architecture (dictionary lookup for 200+ common conversational and tech words + rule-based transliterator with schwa deletion) running in <0.01ms with 0 GPU VRAM.
   - Ensure backward-compatible delegation from `transform_text()` to `format_two_stage()`.
4. **`text_cleaner.py`**:
   - Ensure `format_casual_chat` strips trailing formal periods and commas while keeping Hinglish vocabulary natural.
5. **`voice_profile.py`**:
   - Implement `get_stage2_context()` returning `<personal_dictionary>` and `<phonetic_memory>`.
   - Ensure `get_initial_prompt()` includes target words from `word_replacements`.
   - Ensure `apply_replacements()` performs the deterministic regex post-pass to guarantee 100% dictionary match.
6. **Build & Test Verification**:
   - Run tests: `.venv\Scripts\python.exe -m unittest discover tests`
   - Run whisper tests: `.venv\Scripts\python.exe -m unittest tests/test_whisper_engine.py`
   - Run style engine tests: `.venv\Scripts\python.exe -m unittest tests/test_style_engine.py`
   - Verify all tests pass cleanly.

Report all verification commands and outputs in `handoff.md`.
