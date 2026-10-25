## 2026-10-22T11:47:52Z
[Message] timestamp=2026-10-22T11:47:52Z sender=b7127cef-b446-4dca-a8e7-b0da25424e7e priority=MESSAGE_PRIORITY_HIGH content=You are Worker M3-1 for Whisper Flow Round 2 (Milestone M3: Unified Settings UI & Floating Capsule Badges).
Your working directory is: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m3_it1
Authoritative user request: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md (specifically see ## 2026-10-22T09:54:41Z).
Project architecture: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\PROJECT.md
Survey findings: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your exclusive write ownership:
- ui/settings_dialog.py
- ui/floating_widget.py
- app.py
- config.py

Your tasks:
1. ui/settings_dialog.py:
   - Embed segmented card toggle for Engine Selector:
     * Card 1: "Groq Cloud (Ultra-Fast whisper-large-v3-turbo, 0% CPU & GPU)"
     * Card 2: "Local CPU (int8 Offline)"
     * Toggling saves "engine_mode" to config ("groq" vs "local") and emits `engine_changed = Signal(str)`.
   - Embed live "Test Mic & API Connection" button:
     * Audio stream check: A non-blocking VU meter (QProgressBar, 0-100%) that polls `self.audio_engine.get_current_volume()` via QTimer to display live mic input volume.
     * Groq API key check: In background daemon thread, sends HTTPS request to `https://api.groq.com/openai/v1/models` with headers `{"Authorization": f"Bearer {groq_key}", "User-Agent": "WhisperFlow"}` and 5.0s timeout.
     * Measures round-trip latency. Displays green text with "✓ Connected ({latency}ms latency)" on HTTP 200, or clear red error (e.g. "Authentication Failed (401)", "Invalid Key", or "Offline / Network Timeout").
     * Zero GUI freeze: fully asynchronous and non-blocking.
   - 2x2 Speech Style selection cards in Voice & Styles tab:
     * 4 clickable cards: Casual Chat, Developer Mode, Professional, Custom Persona.
     * Selecting a card updates `VoiceProfileManager.set_active_style()`, emits `style_changed = Signal(str)`, and visually highlights the card.
   - Preserve performance: Keep deferred loading for Personal Dictionary (`_ensure_dictionary_loaded()`), keep `takeItem(i)` for 1-click word removal (<1ms), and preserve dialog launch latency (<50ms).

2. ui/floating_widget.py:
   - Expand idle dock geometry: `self.dock_w = 148` (148x34px).
   - In `paintEvent` for `STATE_IDLE`:
     * Left: 3-bar breathing voice emblem.
     * Center: Live engine status badge: `● Cloud Active` (green) or `● Local CPU` (violet).
     * Right: Language mode badge: `HI-EN` (or `EN`).
   - Implement slot `update_status_badges(self, engine: str, language: str = "hinglish", style: str | None = None)` that updates internal state and triggers `self.update()`.

3. app.py:
   - Connect `SettingsDialog.engine_changed` to `floating_widget.update_status_badges()` and update `whisper_engine.engine_mode`.
   - Connect `language_changed` and `style_changed` signals.
   - Add direct engine toggle (Groq Cloud / Local CPU) and language toggle (Hinglish / English) into tray context menu.

4. config.py:
   - Ensure `"engine_mode": "groq"` and `"language_mode": "hinglish"` are in `DEFAULT_CONFIG`.

Verification:
Execute and document output of:
1. .\.venv\Scripts\python.exe -m unittest tests/test_settings_ui_r2.py
2. .\.venv\Scripts\python.exe -m unittest discover tests (all 231+ tests pass!)
3. .\.venv\Scripts\python.exe benchmark_hinglish.py (20/20 pass!)

Write progress in progress.md, detailed report in handoff.md in your working directory, and call send_message when complete.
