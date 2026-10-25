# Project: Whisper Flow Round 2 — Intelligent Two-Stage Hinglish Pipeline & Desktop Hardening

## Architecture
Whisper Flow is a high-performance, personalized speech-to-text desktop application designed for Windows with zero GPU VRAM consumption, bilingual English & Hindi/Hinglish speech calibration, custom styling, and instant desktop shortcut activation.

Round 2 introduces an intelligent two-stage speech processing pipeline, personal phonetic memory from calibration, an explicit engine switch (Groq Cloud vs Local CPU int8), and a real-time responsive UI with live mic/API diagnostics and floating capsule status badges.

### Subsystems & Data Flow
1. **Intelligent Two-Stage Speech Pipeline**:
   - `whisper_engine.py`:
     - **Stage 1 (Acoustic Capture)**: Transcribes raw spoken audio via Groq Cloud (`whisper-large-v3-turbo` with `task="transcribe"`, no forced translation) or local CPU (`faster-whisper` `base` int8, 0 MB GPU VRAM). Biased with `initial_prompt` containing calibrated target vocabulary.
     - **Stage 2 (Fast Romanizer & Stylist)**: Routes raw transcript through an ultra-low-latency formatter (`llama-3.3-70b-versatile` on Groq Cloud, ~158ms, or local fast CPU Romanizer, <0.01ms) with a dedicated anti-translation prompt. Translates Devanagari to natural Romanized Hinglish (Latin alphabet), preserves English technical terms ("deploy", "server", "github", "commit"), enforces speech style (Casual Chat, Developer Mode, Professional, Custom Persona), and injects `<phonetic_memory>` and `<personal_dictionary>`.
     - **Stage 3 (Deterministic Exact Match Guarantee)**: Applies `VoiceProfileManager.apply_replacements` via lookaround regex to guarantee 100% personal dictionary fidelity.
2. **Smart Voice Calibration & Phonetic Memory**:
   - `data/calibration_sentences.json`: Authoritative dataset of 100 sentences (50 English, 50 natural Romanized Hindi/Hinglish).
   - `calibration_engine.py`: Standalone pure computation module for word-level sequence matching diffs.
   - `ui/voice_training_dialog.py`: Desktop calibration wizard running spoken audio through Stage 1 -> Stage 2 Romanizer before diffing against Romanized calibration target. Displays live accuracy diffs with interactive 1-click confirmation chips (`PhoneticPairChip`) for words the user wants permanently remembered.
   - `voice_profile.py`: Profile manager maintaining custom vocabulary and phonetic replacements (`voice_profile.json`). Injects target replacements into Stage 1 `initial_prompt` and provides structured context for Stage 2 formatter.
3. **Unified Settings UI & Floating Capsule Badges**:
   - `ui/settings_dialog.py`:
     - Explicit Engine Selector segmented card toggle: `Groq Cloud (Ultra-Fast whisper-large-v3-turbo, 0% CPU & GPU)` vs `Local CPU (int8 Offline)`.
     - Live "Test Mic & API Connection" button with non-blocking audio RMS VU meter and Groq API ping measuring round-trip latency.
     - 2x2 clickable Speech Style selection cards (Casual Chat, Developer, Professional, Custom).
     - Preserves sub-50ms dialog open latency (baseline ~18ms) and 0.59ms 1-click dictionary removal via `takeItem(i)`.
   - `ui/floating_widget.py`:
     - Expanded 148x34px idle dock with breathing voice emblem, engine status chip (`Cloud Active` / `Local CPU`), and language chip (`HI-EN` / `EN`).
     - Real-time signal synchronization with `SettingsDialog` and engine mode changes.
4. **Automated Verification & Benchmark**:
   - Automated Hinglish benchmark script (`benchmark_hinglish.py`) verifying 20 spoken Hindi/Hinglish test cases produce natural Romanized Hinglish instead of English translations.
   - Complete unittest suite discoverable via `python -m unittest discover tests` (all 97 existing tests + new pipeline, calibration, and UI tests).

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Stage 1 Acoustic Capture (No Forced Translation) | Groq `whisper-large-v3-turbo` and local CPU `base` int8 with `task="transcribe"`, auto-detecting language | M1 | Survey / R1 |
| F2 | Stage 2 Fast LLM Romanizer & Stylist | Anti-translation prompt on Groq `llama-3.3-70b-versatile` converting Devanagari to Romanized Hinglish | M1 | Survey / R1 |
| F3 | Zero-GPU Local Fast Romanizer Fallback | Pure Python Devanagari Romanizer (<0.01ms) for offline CPU mode | M1 | Survey / R1 |
| F4 | Code & Tech Term Preservation | Guarantee English technical terms ("deploy", "server", "github", "commit") remain in clean English | M1 | Survey / R1 |
| F5 | 100% Personal Dictionary Exact Match | Prompt injection + deterministic lookaround regex post-pass (`apply_replacements`) | M1 | Survey / R1 |
| F6 | Speech Style Transformations | Casual Chat (strip trailing periods/commas), Developer Mode (camelCase, snake_case), Professional, Custom | M1 | Survey / R1 |
| F7 | Sub-350ms End-to-End Latency | Pipeline budget verified under 350ms on Groq Cloud (~283ms actual) | M1 | Survey / R1 |
| F8 | 100 Bilingual Calibration Sentences | 50 English + 50 Romanized Hindi/Hinglish in `data/calibration_sentences.json` | M2 | Survey / R2 |
| F9 | Two-Stage Routing in Calibration Wizard | Route spoken Hindi through Romanizer so output is in Latin alphabet before diffing | M2 | Survey / R2 |
| F10 | Automated Heard -> Target Phonetic Mapper | Register misheard pronunciations into `voice_profile.json` | M2 | Survey / R2 |
| F11 | 1-Click Phonetic Confirmation Chips | Interactive UI chips in calibration wizard allowing 1-click permanent memory | M2 | Survey / R2 |
| F12 | Dual Injection Contract | Target replacements in Stage 1 `initial_prompt` + phonetic memory in Stage 2 context | M2 | Survey / R2 |
| F13 | Explicit Engine Selector Toggle | Segmented cards in Preferences for Groq Cloud vs Local CPU int8, wired to `config.json` | M3 | Survey / R3 |
| F14 | Live Test Mic & API Connection Button | Audio VU meter + background Groq API key ping with live latency display | M3 | Survey / R3 |
| F15 | Direct Speech Style Selection Cards | 2x2 clickable interactive card grid in Preferences for instant style switching | M3 | Survey / R3 |
| F16 | Sub-50ms Dialog Launch & 1-Click Removal | Preserved ~18ms open latency via deferred loading and 0.59ms 1-click dictionary deletion | M3 | Survey / R3 |
| F17 | Floating Capsule Live Status Badges | Expanded 148x34px dock displaying `Cloud Active` / `Local CPU` and `HI-EN` / `EN` chips | M3 | Survey / R3 |
| F18 | Automated 20-Case Hinglish Benchmark | Script verifying 20 Hindi/Hinglish test cases produce natural Romanized Hinglish | E2E & M4 | Survey / R4 |
| F19 | Comprehensive Regression & E2E Test Suite | Run all 97 existing + new unit tests via `python -m unittest discover tests` | E2E & M4 | Survey / R4 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Design & create test infra, 20-case Hinglish benchmark, regression runner, and publish `TEST_READY.md` | none | DONE |
| M1 | Two-Stage Hinglish Pipeline & LLM Romanizer | Implement Stage 1 acoustic capture, Stage 2 Groq llama-3.3-70b-versatile & local fast Romanizer, style transforms, and 100% dictionary guarantee in `whisper_engine.py`, `style_engine.py`, `text_cleaner.py`, `config.py` | none | DONE |
| M2 | Smart Calibration & Phonetic Memory | Wire 100 bilingual sentences, route calibration through Romanizer, implement 1-click confirmation chips, and dual injection contract in `calibration_engine.py`, `voice_profile.py`, `ui/voice_training_dialog.py` | M1 | DONE |
| M3 | Unified Settings UI & Floating Capsule Badges | Implement Engine Selector toggle, live Test Mic & API Connection button, speech style cards, and 148px floating dock with live status badges in `ui/settings_dialog.py`, `ui/floating_widget.py`, `app.py` | M1, M2 | DONE |
| M4 | Final E2E Pass & Adversarial Coverage Hardening | Phase 1: Pass 100% E2E tests & 20-case Hinglish benchmark; Phase 2: Adversarial coverage hardening (Challenger -> Worker -> Reviewer -> Auditor) | E2E, M1, M2, M3 | IN_PROGRESS |

---

## Interface Contracts

### `whisper_engine.py` ↔ `style_engine.py`
- `WhisperEngine.transcribe(audio_data: np.ndarray, sample_rate: int = 16000, initial_prompt: str | None = None, style: str | None = None) -> str`:
  - Stage 1: Captures acoustic audio via Groq `whisper-large-v3-turbo` or local CPU `base` int8 with `task="transcribe"`.
  - Stage 2: Calls `StyleEngine.format_two_stage(raw_transcript, style=style, voice_profile=profile)`.
  - Stage 3: Runs `profile.apply_replacements(formatted_text)` to guarantee 100% dictionary match.
  - Returns final natural Romanized Hinglish text in Latin alphabet.

### `voice_profile.py` ↔ `whisper_engine.py` & `ui/voice_training_dialog.py`
- `VoiceProfileManager.get_initial_prompt(max_chars=800) -> str | None`:
  - Returns `"Vocabulary: <custom_words + unique replacement targets>."` truncated to 800 chars.
- `VoiceProfileManager.get_stage2_context() -> dict`:
  - Returns `{"phonetic_memory": dict(self.get_replacements()), "custom_words": list(self.get_custom_words())}`.

### `ui/settings_dialog.py` ↔ `ui/floating_widget.py` & `app.py`
- Signals:
  - `engine_changed = Signal(str)` ("groq" or "local")
  - `language_changed = Signal(str)` ("hinglish" or "en")
  - `style_changed = Signal(str)` ("casual", "developer", "professional", "custom")
- `FloatingWidget.update_status_badges(engine: str, language: str, style: str | None = None)`:
  - Updates dock rendering immediately without modal lag.

---

## Code Layout
- `app.py`: Desktop lifecycle, single-instance mutex, and signal wiring.
- `config.py` & `config.json`: Configuration (`"engine_mode"`, `"language_mode"`).
- `whisper_engine.py`: Stage 1 acoustic capture (Groq & local CPU int8) and Two-Stage coordination.
- `style_engine.py`: Stage 2 Romanizer and Stylist (Groq `llama-3.3-70b-versatile` & local fast Romanizer, Developer Mode, Persona).
- `text_cleaner.py`: Rule-based cleaner and casual formatter.
- `calibration_engine.py`: Standalone pure diff and alignment engine.
- `voice_profile.py`: Profile manager, phonetic replacements, lookaround regex.
- `data/calibration_sentences.json`: Authoritative 100-sentence dataset (50 English, 50 Hindi/Hinglish).
- `ui/settings_dialog.py`: Preferences dialog, Engine Selector toggle, live Test Mic & API diagnostics, style cards.
- `ui/floating_widget.py`: 148px floating capsule dock with live status badges (`Cloud Active` / `Local CPU`, `HI-EN`).
- `ui/voice_training_dialog.py`: Calibration wizard with live diffs and 1-click confirmation chips.
- `tests/`: Complete test suite discoverable via `python -m unittest discover tests`.
- `benchmark_hinglish.py`: 20-case Hinglish benchmark script.
