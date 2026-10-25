# DISPATCH LOG

## 2026-10-22T09:56:25Z
From: 45cfc7c0-004e-475a-85ff-018a6327a593 (parent)
Priority: MESSAGE_PRIORITY_HIGH

You are the Project Orchestrator for Whisper Flow.

Your working directory is: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator_r2
Project root: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
Authoritative user request: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md (specifically see the latest entry under ## 2026-10-22T09:54:41Z).
Prior round artifacts can be referenced in: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md

Your mission:
Lead the full multi-agent team to build and deploy an intelligent two-stage speech transcription and styling pipeline in Whisper Flow that natively supports natural Romanized Hinglish, automatic personal phonetic memory from calibration, zero-GPU execution, and a unified desktop settings experience with live feedback.

Requirements to implement and verify:
1. R1. Intelligent Two-Stage Hinglish & Multilingual Pipeline:
   - Stage 1 (Acoustic Capture): Whisper (via Groq Cloud whisper-large-v3-turbo or local CPU base) transcribes raw spoken audio without forced English translation.
   - Stage 2 (Fast Romanizer & Stylist): Pass the raw transcript through an ultra-low-latency formatter (Groq llama-3.3-70b-versatile or local engine) with a dedicated prompt that:
     - Transcribes Hindi into natural Romanized Hinglish using the English alphabet (e.g., "Main kal code push kar dunga"), preserving English technical terms and code tokens.
     - Strictly prevents literal translation into English.
     - Directly enforces the user's active speech style (Casual Chat, Developer Mode, Professional, Custom Persona).
     - Guarantees exact matches for all saved personal dictionary words and phonetic corrections.
2. R2. Smart Voice Calibration & Phonetic Memory:
   - Wire the 100 bilingual calibration sentences (50 English, 50 Hindi/Hinglish in data/calibration_sentences.json) to automatically detect user pronunciation variances.
   - When Whisper mishears a user's word or pronunciation, automatically register the Heard -> Target mapping into voice_profile.json and inject it directly into the Stage 2 formatter context.
   - Ensure the calibration wizard displays live accuracy diffs with 1-click confirmation for words the user wants permanently remembered.
3. R3. Unified Settings UI & Real-Time Widget Feedback:
   - Redesign the Preferences panel with:
     - An explicit Engine Selector toggle: Groq Cloud (Ultra-Fast whisper-large-v3-turbo, 0% CPU & GPU) vs Local CPU (int8 Offline).
     - A live Test Mic & API Connection button that checks microphone levels and verifies the Groq API key with live latency display.
     - Direct speech style selection cards (Casual Chat, Developer, Professional, Custom).
   - Update the floating capsule widget to show live status badges (e.g., Cloud Active, Local CPU, Hinglish, Transcribing...).
   - Preserve sub-50ms dialog launch times and 1-click dictionary word removal.
4. Verification & Acceptance Criteria:
   - Test suite runner script: python -m unittest discover tests
   - Automated Hinglish benchmark script: verify 20 spoken Hindi/Hinglish test cases produce natural Romanized Hinglish instead of English translations.
   - Hindi audio input produces natural Romanized Hinglish text (Latin alphabet) rather than literal English translations or Devanagari script.
   - Technical English words spoken in Hinglish sentences (e.g., "deploy", "server", "github", "commit") remain in clean English.
   - Saved personal dictionary words appear with 100% fidelity in output text.
   - Casual Chat style strips trailing periods and commas while keeping Hinglish text natural.
   - End-to-end two-stage transcription pipeline completes in under 350ms on Groq Cloud.
   - Preferences panel clearly exposes the engine switch with a working "Test Connection" button.
   - Floating dock reflects current active engine and language status.
   - All 97 existing automated tests + new Hinglish pipeline tests pass cleanly.
