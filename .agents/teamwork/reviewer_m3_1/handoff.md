# Milestone M3 Review & Adversarial Challenge Report

**Reviewer**: Reviewer M3-1 (`reviewer_m3_1`)  
**Target Milestone**: M3 — Unified Settings UI & Floating Capsule Badges  
**Authoritative Request**: `ORIGINAL_REQUEST.md` (specifically `## 2026-10-22T09:54:41Z`)  
**Project Architecture**: `PROJECT.md`  
**Worker Handoff**: `worker_m3_it1/handoff.md`  
**Verdict**: **APPROVE**  
**Overall Risk Assessment**: **LOW**

---

## 1. Observation

Direct observations from independent code review, static inspection, adversarial scenario testing, and automated test execution:

1. **Configuration Defaults & Fallbacks (`config.py`)**:
   - `DEFAULT_CONFIG` at lines 11-12 defines:
     ```python
     "engine_mode": "groq",      # "groq" or "local"
     "language_mode": "hinglish", # "hinglish" or "en"
     ```
   - In `load_config()` (lines 27-29), `DEFAULT_CONFIG.copy()` is updated with file contents, guaranteeing that legacy configurations missing these keys default cleanly without `KeyError`.

2. **Preferences Dialog Architecture (`ui/settings_dialog.py`)**:
   - **EngineCard Toggle** (lines 125-204, 468-495):
     - Implements `EngineCard` widget with high-contrast active borders (`#3b82f6`), selection state badges (`RECOMMENDED` / `OFFLINE`), and click handlers.
     - `_set_engine_mode(mode)` sets `self.engine_mode`, updates `self.config["engine_mode"]`, updates `whisper_engine.engine_mode`, toggles card selection visuals, and emits `self.engine_changed.emit(mode)`.
   - **Live Mic VU Meter & Diagnostic API Ping** (lines 277, 518-583, 1030-1137):
     - `self.vu_meter`: `QProgressBar` (range 0 to 100) with gradient styling (`#10b981` to `#38bdf8`).
     - Polled via `self._vu_timer` (40ms interval) querying `audio_engine.get_current_volume()`.
     - Automatically terminates after 5.0 seconds or upon dialog exit/save (`reject()`, `closeEvent()`, `_save_and_accept()`), cleanly stopping recording if started by the test.
     - `_start_groq_ping_test()` dispatches a background daemon thread querying `https://api.groq.com/openai/v1/models` with `timeout=5.0` and `User-Agent: WhisperFlow`.
     - Result reporting is strictly decoupled via `_api_test_result_signal.emit(success, message)` to ensure thread safety; updates to `test_conn_btn` and `conn_status_lbl` occur exclusively on the Qt GUI thread.
   - **2x2 Speech Style Selection Cards** (lines 206-272, 606-674, 1007-1029):
     - `StyleCard` grid presents Casual Chat, Developer Mode, Professional, and Custom Persona with checkmark indicators (`✓`).
     - Clicking any card invokes `_select_style(key)`, updating `voice_profile_manager.set_active_style(norm_key)` and emitting `style_changed.emit(norm_key)`.
   - **Sub-50ms Launch & 1-Click Removal Preservation** (lines 443-446, 823-828, 876-889, 938-951):
     - Deferred loading pattern: `_dictionary_loaded` guard with `QTimer.singleShot(0, self._ensure_dictionary_loaded)` prevents startup blocking.
     - 1-click removal methods (`_on_remove_word_clicked` and `_on_remove_rep_clicked`) call `takeItem(i)` directly in-place without rebuilding the widget tree.

3. **Floating Capsule Dock Geometry & Live Status Badges (`ui/floating_widget.py`)**:
   - Idle capsule dock dimensions (lines 58-60):
     ```python
     self.dock_w = 148
     self.dock_h = 34
     self.dock_radius = 17.0
     ```
   - Slot `update_status_badges(self, engine: str, language: str = "hinglish", style: str | None = None)` (lines 185-195) supports 1-, 2-, and 3-argument calls, updating `active_engine`, `active_language`, and `active_style` with immediate repaint (`self.update()`).
   - `paintEvent` under `STATE_IDLE` (lines 375-452):
     - Left (x=7 to ~32px): 3-bar voice emblem breathing gently via sine wave animation.
     - Center (x=42 to 115px): Status dot (5px) and label (`● Cloud Active` in emerald `#10B981` / `#34D399` or `● Local CPU` in violet `#A855F7` / `#C4B5FD`).
     - Right (x=118 to 146px): Language chip (`HI-EN` in `#93C5FD` or `EN`) inside rounded chip boundary.
     - Verified geometric clearances: 10px buffer between emblem and center badge; 3px buffer between center badge text and right language chip; 9px right capsule margin. Zero overlap or text truncation.
   - Context Menu (lines 264-353):
     - Added Engine Submenu ("Groq Cloud (0% CPU)" vs "Local CPU (int8 Offline)") with live checkmarks.
     - Added Language Submenu ("Hinglish" vs "English Only") with live checkmarks.

4. **Application Wiring & Tray Menu Integration (`app.py`)**:
   - Initialized badges on startup (lines 160-165):
     ```python
     self.whisper_engine.engine_mode = init_engine
     self.widget.update_status_badges(init_engine, init_lang, init_style)
     ```
   - Bound signals (lines 208-212, 660-662):
     - `self.widget.engine_changed.connect(self._on_engine_changed)`
     - `self.widget.language_changed.connect(self._on_language_changed)`
     - `dlg.engine_changed.connect(self._on_engine_changed)`
     - `dlg.language_changed.connect(self._on_language_changed)`
     - `dlg.style_changed.connect(self._on_style_changed)`
   - System Tray context menu (lines 398-423, 466-475):
     - Added "Engine Mode" and "Language Mode" submenus with bidirectional synchronization helper `_sync_tray_engine_and_lang()`.

5. **Independent Test Execution Results**:
   - `.\.venv\Scripts\python.exe -m unittest -v tests/test_settings_ui_r2.py`:
     - **16 tests run, 16 passed, 0 failures, 0 errors** in **0.326s**.
   - `.\.venv\Scripts\python.exe -m unittest discover tests`:
     - **237 tests run, 237 passed, 0 failures, 0 errors** in **7.532s**.
     - Benchmark measurements recorded:
       - `SettingsDialog Open Latency (10 cycles)`: Mean 11.19ms, Min 8.18ms, Max 14.47ms (SLA < 50ms).
       - `VoiceTrainingDialog Open Latency`: Mean 14.58ms, Max 27.87ms (SLA < 50ms).
       - `1-Click Word Removal Latency`: 0.7991ms (SLA < 1ms).
       - `1-Click Replacement Rule Removal Latency`: 0.5358ms (SLA < 1ms).
       - `Subprocess Exit Latency`: 88.01ms (SLA < 100ms).
   - `.\.venv\Scripts\python.exe benchmark_hinglish.py`:
     - **20/20 Hinglish test cases passed (100.0% pass rate)**.
     - Mean CPU latency: 6.7092 ms (Budget: <200 ms).
     - Max latency: 125.7231 ms (Budget: <200 ms).

---

## 2. Logic Chain

1. **Integrity Assessment**:
   - Inspected source code across `ui/settings_dialog.py`, `ui/floating_widget.py`, `app.py`, and `config.py`.
   - Verified that all widgets implement real logic: `EngineCard` and `StyleCard` capture clicks and mutate system state; `vu_meter` measures live audio RMS; `_start_groq_ping_test()` issues real HTTP requests with timeouts and headers; `FloatingWidget` dynamically renders live badges in `paintEvent` without dummy facades.
   - Verified that test suites in `tests/test_settings_ui_r2.py` test actual behavior and contract fulfillment rather than bypassing logic or hardcoding outputs.
   - **Integrity Finding**: **PASS** (Zero integrity violations found).

2. **Quality & Correctness Assessment**:
   - The EngineCard toggle cleanly switches between Groq Cloud and Local CPU, persisting `"engine_mode"` in `config.json` and switching `whisper_engine.engine_mode` immediately.
   - The live microphone VU meter and API connection test run without blocking the GUI event loop. API ping results route via Qt Signals, preventing cross-thread UI crashes.
   - The 2x2 speech style cards accurately synchronize with `VoiceProfileManager`, persisting choices across sessions and updating tray checkmarks.
   - The floating capsule dock was expanded to 148x34px, crisply displaying the voice emblem, engine status (`Cloud Active` / `Local CPU`), and language chip (`HI-EN` / `EN`) with zero visual overlap.
   - Latency SLAs are fully satisfied: SettingsDialog presentation operates at ~11.19ms (<50ms SLA), and dictionary item deletion operates at ~0.53-0.79ms (<1ms SLA).

3. **Adversarial Stress Testing & Boundary Analysis**:
   - **Scenario 1: Dialog Cancellation mid-Audio Test**:
     - *Attack*: User clicks "Test Mic & API Connection" and closes or cancels the dialog while the 5-second VU meter is active.
     - *Observation*: `reject()`, `closeEvent()`, and `_save_and_accept()` explicitly call `_stop_audio_vu_test()`.
     - *Result*: Timer stops, audio recording cleanly terminates if started by the test, and progress bar resets to 0. No thread or audio resource leaks.
   - **Scenario 2: Network Outage / Invalid API Key during Ping**:
     - *Attack*: User clicks "Test Connection" with empty key, malformed key, HTTP 401, or no network connectivity.
     - *Observation*: Empty key is rejected before thread launch with clear warning label. HTTP errors (401, 429, 503) and network timeouts (`URLError`) are trapped within the worker and delivered via `_api_test_result_signal`.
     - *Result*: Test button re-enables; UI displays red failure status without freezing the application.
   - **Scenario 3: Legacy Configuration Migration**:
     - *Attack*: Application launched with older `config.json` lacking `engine_mode` or `language_mode`.
     - *Observation*: `load_config()` merges existing JSON over `DEFAULT_CONFIG.copy()`. All components call `.get("engine_mode", "groq")`.
     - *Result*: Defaults gracefully to `"groq"` and `"hinglish"` without throwing `KeyError`.
   - **Scenario 4: High-Frequency Rapid Toggle**:
     - *Attack*: Repeatedly clicking engine and style cards in milliseconds.
     - *Observation*: Mutex and Qt signal slots handle synchronous property assignment; lookups in `self.style_cards` and `self.engine_action_group` execute in O(1) time.

---

## 3. Caveats

- **No Caveats**: All requested modifications (`config.py`, `ui/settings_dialog.py`, `ui/floating_widget.py`, `app.py`, and `tests/test_settings_ui_r2.py`) were implemented cleanly within assigned file boundaries, leaving untouched core pipelines unaffected. All 237 test cases in the test suite pass.

---

## 4. Conclusion

Milestone M3 (Unified Settings UI & Floating Capsule Badges) is completely implemented, verified, and adheres to all architectural requirements and quality standards:
- **EngineCard Toggle**: Flawlessly toggles between Groq Cloud and Local CPU int8 with immediate config and runtime engine update.
- **Microphone & API Diagnostics**: Non-blocking audio RMS VU meter and thread-safe Groq API ping operate smoothly with zero GUI freeze.
- **2x2 Speech Style Cards**: Interactive selection grid accurately synchronizes with `VoiceProfileManager` and tray menus.
- **148x34px Floating Capsule**: Crisp obsidian pill layout displays live 3-bar emblem, engine badge (`● Cloud Active` / `● Local CPU`), and language badge (`HI-EN` / `EN`).
- **Performance Preservation**: Sub-50ms dialog launch (~11.19ms) and <1ms dictionary removal (~0.53-0.79ms) verified.
- **Test Suite**: 16/16 M3 unit tests, 237/237 full suite tests, and 20/20 Hinglish benchmark tests pass with 100% success.

**Final Verdict: APPROVE**

---

## 5. Verification Method

To independently verify the implementation, execute the following commands in PowerShell from the repository root:

1. **Verify Dedicated M3 Test Suite**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest -v tests/test_settings_ui_r2.py
   ```
   *Expected*: 16/16 tests pass with `OK` status in <0.5s.

2. **Verify Full Discoverable Test Suite**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover tests
   ```
   *Expected*: 237/237 tests pass with `OK` status in ~7-8s, displaying sub-25ms open latency and sub-1ms dictionary deletion.

3. **Verify Hinglish Benchmark Suite**:
   ```powershell
   .\.venv\Scripts\python.exe benchmark_hinglish.py
   ```
   *Expected*: 20/20 tests pass with 100% pass rate and mean CPU latency under 10ms.
