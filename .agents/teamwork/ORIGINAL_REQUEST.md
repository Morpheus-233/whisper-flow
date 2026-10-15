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
