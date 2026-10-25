# Original User Request

## 2026-10-15T14:45:23Z

Requested team: Full multi-agent team

Build and harden Whisper Flow into a production-grade, personalized speech-to-text desktop system that supports bilingual English and Hindi/Hinglish speech calibration, zero-GPU low-latency transcription, custom speech styling, and instant desktop shortcut activation.

Working directory: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
Integrity mode: development

## Requirements

### R1. Bilingual Speech Adaptation & Calibration (English + Hindi/Hinglish)
- Provide a 100-sentence voice calibration dataset (50 phonetically rich English sentences, 50 natural conversational Hindi and Hinglish technical sentences).
- Implement an automated accuracy diff and phonetic correction mapper: when Whisper misrecognizes a Hinglish or spoken English word, automatically register the target phonetic mapping into the user's voice_profile.json.
- Inject custom vocabulary biasing (initial_prompt) into the Whisper decoding loop to guide token probabilities towards the user's calibrated vocabulary.

### R2. Zero-GPU High-Efficiency Speech Engine & Style Processing
- Support CPU int8 execution (WhisperModel(model_name, device='cpu', compute_type='int8')) with zero GPU VRAM consumption, alongside optional high-speed cloud transcription fallback (Groq Whisper API) for sub-100ms response times.
- Implement instant rule-based speech style transformations:
  - Casual Chat: Strips trailing formal periods, commas, and robotic capitalization.
  - Developer Mode: Transforms spoken commands into camelCase, snake_case, and code syntax.
  - Custom Persona: Formats output to match custom user-defined tone without adding latency.

### R3. Desktop Lifecycle, Single-Instance Management & UI Responsiveness
- Enforce atomic single-instance lifecycle using a Windows named mutex and IPC server.
- Double-clicking the desktop icon while an instance is running must immediately grant foreground activation rights (AllowSetForegroundWindow) and bring the floating capsule and Preferences dialog front-and-center.
- Ensure all dialogs (Preferences, Voice Calibration Wizard) open in under 50ms with native immersive dark title bars (DWMWA_USE_IMMERSIVE_DARK_MODE) and zero Win32 mouse capture deadlock.
- Provide 1-click instant word and replacement rule removal with real-time search filtering.

## Verification Resources

- Test suite runner script: python -m unittest discover tests
- Dataset: data/calibration_sentences.json (100 bilingual sentences)
- Profile manager: voice_profile.py verifying vocabulary and phonetic replacement rules

## Acceptance Criteria

### Desktop Lifecycle & IPC
- [ ] Running a second instance via pythonw.exe app.py while Whisper Flow is active exits immediately in under 100ms and brings the existing instance to the foreground.
- [ ] Preferences and Voice Calibration dialogs open in under 50ms with dark title bars and zero mouse capture lock.

### Speech Calibration & Dictionary
- [ ] Calibration suite loads 100 bilingual sentences (50 English, 50 Hindi/Hinglish) and computes accurate diffs against user speech.
- [ ] Misheard words added to dictionary are correctly replaced during subsequent live dictation.
- [ ] Dictionary entries can be deleted with a single click in 0ms without UI freezing.

### Style Transformation
- [ ] Casual style removes trailing periods and commas from test inputs without invoking GPU-heavy LLM passes.
- [ ] Custom persona rules apply correctly to output transcriptions.


## 2026-10-22T09:54:41Z

Requested team: Full multi-agent team

Build and deploy an intelligent two-stage speech transcription and styling pipeline in Whisper Flow that natively supports natural Romanized Hinglish, automatic personal phonetic memory from calibration, zero-GPU execution, and a unified desktop settings experience with live feedback.

Working directory: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
Integrity mode: development

## Requirements

### R1. Intelligent Two-Stage Hinglish & Multilingual Pipeline
- Implement a two-stage speech processing architecture:
  - **Stage 1 (Acoustic Capture)**: Whisper (via Groq Cloud `whisper-large-v3-turbo` or local CPU `base`) transcribes raw spoken audio without forced English translation.
  - **Stage 2 (Fast Romanizer & Stylist)**: Pass the raw transcript through an ultra-low-latency formatter (Groq `llama-3.3-70b-versatile` or local engine) with a dedicated prompt that:
    - Transcribes Hindi into natural **Romanized Hinglish** using the English alphabet (e.g., *"Main kal code push kar dunga"*), preserving English technical terms and code tokens.
    - Strictly prevents literal translation into English.
    - Directly enforces the user's active speech style (Casual Chat, Developer Mode, Professional, Custom Persona).
    - Guarantees exact matches for all saved personal dictionary words and phonetic corrections.

### R2. Smart Voice Calibration & Phonetic Memory
- Wire the 100 bilingual calibration sentences (50 English, 50 Hindi/Hinglish) to automatically detect user pronunciation variances.
- When Whisper mishears a user's word or pronunciation, automatically register the `Heard -> Target` mapping into `voice_profile.json` and inject it directly into the Stage 2 formatter context.
- Ensure the calibration wizard displays live accuracy diffs with 1-click confirmation for words the user wants permanently remembered.

### R3. Unified Settings UI & Real-Time Widget Feedback
- Redesign the Preferences panel with:
  - An explicit **Engine Selector** toggle: `Groq Cloud (Ultra-Fast whisper-large-v3-turbo, 0% CPU & GPU)` vs `Local CPU (int8 Offline)`.
  - A live **Test Mic & API Connection** button that checks microphone levels and verifies the Groq API key with live latency display.
  - Direct speech style selection cards (Casual Chat, Developer, Professional, Custom).
- Update the floating capsule widget to show live status badges (e.g., `Cloud Active`, `Local CPU`, `Hinglish`, `Transcribing...`).
- Preserve sub-50ms dialog launch times and 1-click dictionary word removal.

## Verification Resources

- Test suite runner script: `python -m unittest discover tests`
- Automated Hinglish benchmark script: verify 20 spoken Hindi/Hinglish test cases produce natural Romanized Hinglish instead of English translations.
- Dataset: `data/calibration_sentences.json`

## Acceptance Criteria

### Hinglish & Speech Accuracy
- [ ] Hindi audio input produces natural Romanized Hinglish text (Latin alphabet) rather than literal English translations or Devanagari script.
- [ ] Technical English words spoken in Hinglish sentences (e.g., *"deploy"*, *"server"*, *"github"*, *"commit"*) remain in clean English.
- [ ] Saved personal dictionary words appear with 100% fidelity in output text.

### Speech Styles & Latency
- [ ] Casual Chat style strips trailing periods and commas while keeping Hinglish text natural.
- [ ] End-to-end two-stage transcription pipeline completes in under 350ms on Groq Cloud.

### UI & Engine Controls
- [ ] Preferences panel clearly exposes the engine switch (Groq Cloud vs Local CPU) with a working "Test Connection" button.
- [ ] Floating dock reflects current active engine and language status.
- [ ] All 97 existing automated tests + new Hinglish pipeline tests pass cleanly.
