# Handoff Report: Stage 1 Acoustic Capture Investigation (`whisper_engine.py`)

**Milestone**: M1 (Two-Stage Hinglish Pipeline)  
**Agent**: M1 Explorer 1 (`explorer_m1_1`)  
**Type**: Hard Handoff (Investigation Complete)  
**Date**: 2026-10-22T10:16:00Z  

---

## 1. Observation

1. **`whisper_engine.py` Lines 206–211**:
   ```python
   add_field("model", "whisper-large-v3-turbo")
   add_field("response_format", "json")
   add_field("temperature", "0.0")
   if initial_prompt:
       add_field("prompt", initial_prompt)
   ```
   No `language` parameter is accepted or added to `_transcribe_groq`.
2. **`whisper_engine.py` Lines 222–231**:
   ```python
   req = urllib.request.Request(
       "https://api.groq.com/openai/v1/audio/transcriptions",
       data=payload,
       headers={
           "Authorization": f"Bearer {api_key.strip()}",
           "Content-Type": f"multipart/form-data; boundary={boundary}",
           "User-Agent": "WhisperFlow"
       },
       method="POST"
   )
   ```
   The Groq endpoint is specifically `/openai/v1/audio/transcriptions` with timeout set to `10.0` seconds (line 233).
3. **`whisper_engine.py` Lines 281–290**:
   ```python
   segments, info = self.model.transcribe(
       audio_data,
       initial_prompt=initial_prompt,
       beam_size=1,
       best_of=1,
       temperature=0.0,
       vad_filter=True,
       vad_parameters=dict(min_silence_duration_ms=300),
       condition_on_previous_text=False
   )
   ```
   In the local CPU `faster-whisper` transcription call, neither `task="transcribe"` nor `language=None` is explicitly passed in keyword arguments.
4. **`config.json` Lines 1–5**:
   ```json
   {
       "model_name": "base.en",
       "device": "cpu",
       "compute_type": "int8",
       "groq_api_key": "gsk_placeholder_redacted_for_security",
   ```
   The model name was set to English-only `"base.en"`. Neither `"engine_mode"` nor `"language_mode"` keys were present in `config.py` default config or `config.json`.
5. **Urllib Groq Probe Execution**:
   Executing a probe to Groq API with the configured key output:
   `Groq exception: <class 'urllib.error.HTTPError'> HTTP Error 401: Unauthorized`
   And `whisper_engine.py` logged:
   `[WhisperEngine] Groq API transcription failed: HTTP Error 401: Unauthorized. Falling back to local model.`
   And proceeded to run the local model without unhandled exceptions.
6. **Test Suite Execution**:
   Command: `.venv\Scripts\python.exe -m unittest discover tests`
   Ran 97 tests; all 6 tests in `tests/test_whisper_engine.py` passed cleanly.
7. **`PROJECT.md` Interface Contract Lines 72–77**:
   ```markdown
   - `WhisperEngine.transcribe(audio_data: np.ndarray, sample_rate: int = 16000, initial_prompt: str | None = None, style: str | None = None) -> str`:
     - Stage 1: Captures acoustic audio via Groq `whisper-large-v3-turbo` or local CPU `base` int8 with `task="transcribe"`.
     - Stage 2: Calls `StyleEngine.format_two_stage(raw_transcript, style=style, voice_profile=profile)`.
     - Stage 3: Runs `profile.apply_replacements(formatted_text)` to guarantee 100% dictionary match.
     - Returns final natural Romanized Hinglish text in Latin alphabet.
   ```

---

## 2. Logic Chain

1. **Anti-Translation Invariance**:
   - From (1) and (2), Groq strictly distinguishes translation from transcription via separate REST endpoints (`/audio/transcriptions` vs `/audio/translations`). By strictly targeting `/openai/v1/audio/transcriptions`, Groq cannot trigger Whisper's translation token.
   - From (3), `faster-whisper` allows specifying `task="transcribe"`. Explicitly setting `task="transcribe"` guarantees local CPU decoding will never emit English translations for Hindi speech.
2. **Language Auto-Detection for Hinglish**:
   - Hinglish is inherently code-mixed (Devanagari Hindi phrases interleaved with English technical terms like "deploy", "server", "github").
   - If `language="en"` is forced, Hindi speech is mangled into English phonemes; if `language="hi"` is forced, English technical words risk being forced into Devanagari script (e.g. 'डिप्लॉय').
   - By omitting `language` from Groq API calls and passing `language=None` to `faster-whisper` when language is `None` or `"auto"`, Whisper performs frame-level acoustic language identification, transcribing English in Latin script and Hindi in Devanagari.
   - This raw mixed acoustic output is the ideal input for Stage 2 Romanizer (`StyleEngine.format_two_stage`).
3. **Model Name Sanitization**:
   - From (4), an English-only model (`base.en`) lacks Devanagari tokens and breaks bilingual execution.
   - Therefore, `WhisperEngine.__init__` and `get_instance` must sanitize any `.en` suffix to `"base"`.
4. **Decoupled Interface Design**:
   - From (7), `WhisperEngine` needs a dedicated method `transcribe_stage1(audio_data, sample_rate=16000, initial_prompt=None, language=None, engine_mode=None)` to produce raw acoustic text for Stage 2.
   - `WhisperEngine.transcribe(...)` can then coordinate Stage 1 -> Stage 2 -> Stage 3 cleanly.
5. **Resilient Local CPU Fallback**:
   - From (5), network requests are subject to 401 unauthorized, 429 rate limit, 503 outage, or offline conditions.
   - Checking `engine_mode == "local"` bypasses Groq entirely when local mode is selected.
   - Wrapping Groq calls in a `try...except Exception` block with a tightened 5-second timeout ensures that any cloud failure immediately falls back to `_transcribe_local` without user-visible crashes.

---

## 3. Caveats

1. **Stage 2 Implementation**: This report designs the Stage 1 acoustic output and the coordination interface in `whisper_engine.py`. The actual Groq Llama 3.3 70B prompt and local transliteration engine in `style_engine.py` are scoped to M1 Explorer 2 (`explorer_m1_2`).
2. **Deterministic Dictionary Post-Pass**: Stage 3 exact dictionary replacement via `VoiceProfileManager.apply_replacements` is scoped to M1 Explorer 3 (`explorer_m1_3`).
3. **Groq API Key Validity**: The key currently in `config.json` returned HTTP 401. All tests for Groq functionality must mock network calls to prevent test runner flakiness.

---

## 4. Conclusion

`whisper_engine.py` must be upgraded with the following concrete architectural changes:
1. **Explicit `task="transcribe"`**:
   - Local CPU: explicitly pass `task="transcribe"` in `self.model.transcribe()`.
   - Groq Cloud: ensure strict routing to `/openai/v1/audio/transcriptions`.
2. **Language Auto-Detection**:
   - Accept `language: str | None = None`. Omit on Groq when `None` or `"auto"`; pass `language=None` on local CPU. If `"hi"` or `"en"` is specified, pass the ISO code.
3. **Model Sanitization**:
   - Automatically convert any model name ending in `.en` to multilingual `"base"`.
4. **Decoupled Stage 1 Method**:
   - Introduce `transcribe_stage1(audio_data, sample_rate=16000, initial_prompt=None, language=None, engine_mode=None) -> str`.
5. **Configurable Failover**:
   - Check `engine_mode != "local"` and `groq_key`. Reduce Groq timeout to 5.0 seconds. Catch all network/HTTP errors and fall back to local CPU int8 model.
6. **Two-Stage Coordination in `transcribe()`**:
   - Coordinate `transcribe_stage1` -> `StyleEngine.format_two_stage` -> `VoiceProfileManager.apply_replacements`.

Full drop-in implementation blueprints and unit tests are documented in `analysis.md`.

---

## 5. Verification Method

To independently verify these findings and blueprints:
1. **Inspect Blueprint**: Review `analysis.md` in `.agents/teamwork/explorer_m1_1/analysis.md`.
2. **Run Existing Test Suite**:
   ```powershell
   .venv\Scripts\python.exe -m unittest discover tests
   ```
3. **Run Whisper Engine Tests**:
   ```powershell
   .venv\Scripts\python.exe -m unittest tests/test_whisper_engine.py
   ```
4. **Inspect Source Locations**:
   - Check `whisper_engine.py` lines 175–302 for Groq form generation and local transcribe calls.
   - Check `config.py` lines 6–18 for default configuration schema.
5. **Invalidation Condition**:
   - If Groq's `/audio/transcriptions` endpoint translates Hindi into English, or if `model.transcribe(task="transcribe")` translates Hindi into English, this logic chain would be invalidated. Both have been verified via documentation and upstream Whisper specifications to guarantee native transcription.
