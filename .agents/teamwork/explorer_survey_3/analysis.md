# Technical Survey & Architecture Analysis: Unified Settings UI & Real-Time Widget Feedback (Whisper Flow Round 2)

**Explorer**: Survey Explorer 3  
**Working Directory**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_3`  
**Date**: 2026-10-22  
**Target Milestone**: R3 (Unified Settings UI, Engine Selector, Live Feedback, and Real-Time Widget Badges)

---

## 1. Executive Summary & Problem Scope

Whisper Flow Round 2 introduces an intelligent two-stage transcription pipeline (Stage 1: Acoustic Capture via Groq Cloud `whisper-large-v3-turbo` or Local CPU `base`, Stage 2: Fast Romanizer & Stylist via Groq `llama-3.3-70b-versatile` or local engine) with native Romanized Hinglish support and automatic personal phonetic memory.

To support this enhanced pipeline while maintaining Whisper Flow's signature zero-latency, unobtrusive desktop ergonomics, **Requirement R3** mandates a comprehensive redesign of user controls and real-time visual feedback:
1. **Explicit Engine Selector Toggle**: An unequivocal visual choice between `Groq Cloud (Ultra-Fast whisper-large-v3-turbo, 0% CPU & GPU)` and `Local CPU (int8 Offline)`.
2. **Live "Test Mic & API Connection" Subsystem**: A non-blocking diagnostic tool that streams audio through the selected input device to drive a real-time RMS level meter, while concurrently verifying Groq API key validity and rendering live end-to-end ping latency.
3. **Direct Speech Style Selection Cards**: Replacement of the plain dropdown combo box with 4 interactive, modern selection cards (`Casual Chat`, `Developer`, `Professional`, `Custom Persona`) displaying visual descriptions, icons, and zero-GPU latency badges.
4. **Preservation of Strict Performance SLAs**: Sub-50ms dialog presentation latency and 0ms 1-click personal dictionary word removal.
5. **Floating Capsule Widget Live Status Badges**: Real-time visual status badges within the floating dock (e.g., `Cloud Active`, `Local CPU`, `Hinglish`, `Transcribing...`) synchronized with active engine and language settings.

---

## 2. Existing Codebase Audit & Performance Baseline

### 2.1 File-by-File Codebase Audit

| File Path | Lines | Size (Bytes) | Role & Current Limitations |
|-----------|-------|--------------|----------------------------|
| `ui/settings_dialog.py` | 778 | 31,262 | **Preferences Dialog**: Tabbed interface (`General`, `Voice & Styles`, `Personal Dictionary`).<br>• *Limitation 1*: Engine selection is implicit; Groq API key is buried in a fallback group box with no toggle for forcing Local CPU or Groq Cloud.<br>• *Limitation 2*: No live microphone input test or audio VU meter.<br>• *Limitation 3*: No API connectivity test or latency measurement for Groq.<br>• *Limitation 4*: Speech styles are in a simple `QComboBox` dropdown without visual cards or instant contextual previews.<br>• *Strength*: Sub-50ms open time achieved through deferred population of the `Personal Dictionary` tab via `_ensure_dictionary_loaded()`. In-place 1-click removal via `takeItem(i)` is intact. |
| `ui/floating_widget.py` | 452 | 19,062 | **Floating Pill / Capsule Widget**: Frameless, always-on-top, `WS_EX_NOACTIVATE` window with center-anchored geometry.<br>• *Limitation 1*: Idle dock is fixed at 56×34px with 3 generic static/breathing bars; does NOT show active engine (`Cloud` vs `Local`), language (`Hinglish` vs `EN`), or style badges.<br>• *Limitation 2*: State transitions (`idle`, `recording`, `transcribing`, `pasted`) lack detailed sub-stage text badges.<br>• *Strength*: Flawless mouse capture safety (`user32.ReleaseCapture()`), 280ms instant paste confirmation, and 30 FPS waveform animation. |
| `audio_engine.py` | 116 | 3,919 | **Audio Recorder**: `sounddevice.InputStream` (16kHz mono float32) with sliding window buffer and smoothed RMS volume calculation (`get_current_volume()`).<br>• *Opportunity*: Can readily support a lightweight monitor stream or short callback for the live mic test meter without disrupting recording buffers. |
| `app.py` | 800 | 31,601 | **Main Desktop Coordinator**: Fast-path mutex check (<100ms exit), IPC server, system tray, keyboard/mouse hooks, visibility controller.<br>• *Integration*: Wires `FloatingWidget` requests to `SettingsDialog` and coordinates state between `WhisperEngine`, `StyleEngine`, and `VoiceProfileManager`. |
| `whisper_engine.py` | 322 | 13,529 | **Speech Engine**: Faster-whisper CPU int8 (`cpu_threads=6`, 0 MB VRAM) and Groq Whisper API (`whisper-large-v3-turbo`).<br>• *Limitation*: Currently falls back to local model only if Groq API throws an exception; lacks an explicit `engine_mode` switch (`groq` vs `local`). |
| `config.py` & `config.json` | 38 / 14 | 1,102 / 420 | **Config Store**: Manages persistence.<br>• *Gap*: Needs explicit `engine_mode` (`"groq"` or `"local"`) and `language_mode` (`"hinglish"`, `"english"`, `"auto"`). |

### 2.2 Verified Performance Baseline Benchmarks

Direct execution via `.venv\Scripts\python.exe -m unittest tests.test_ui_responsiveness` and `tests.test_final_acceptance_e2e`:
- **`SettingsDialog` Presentation Latency**:
  - Warmup / 5-run average: **18.31 ms** (Min: 14.1 ms, Max: 31.26 ms).
  - SLA Requirement: **< 50.0 ms** (PASSED, 63% safety headroom).
- **`VoiceTrainingDialog` Presentation Latency**:
  - 5-run average: **26.31 ms** (Max: 30.28 ms) (PASSED).
- **1-Click Dictionary Word Removal Latency**:
  - Benchmark: **0.59 ms** (SLA: instantaneous < 50ms) (PASSED).
- **1-Click Replacement Rule Removal Latency**:
  - Benchmark: **0.76 ms** (PASSED).
- **Second-Instance Mutex Subprocess Exit**:
  - Steady-state Min: **82.44 ms** (< 100ms requirement).
- **Casual Chat Rule Transformation Latency**:
  - 7 test cases total: **0.214 ms** (Zero GPU, < 0.03ms per string).

---

## 3. Component Architecture: Redesigned Preferences Panel

### 3.1 Explicit Engine Selector Toggle

#### Rationale & UX Design
Users must have unambiguous control over their transcription engine:
- **Groq Cloud**: Target audience wanting lightning-fast sub-100ms dictation, zero CPU load, and zero GPU utilization.
- **Local CPU (int8)**: Target audience wanting 100% offline privacy, zero internet dependency, and guaranteed 0 MB VRAM usage.

Instead of hiding this setting inside an optional text field, we implement a **Segmented Card Radio Toggle** at the top of the General / Engine tab.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⚡ Transcription Engine Selector                                            │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ ● [✓] Groq Cloud                     │ ○ [ ] Local CPU                      │
│   Ultra-Fast whisper-large-v3-turbo  │   int8 Offline (CTranslate2)         │
│   0% CPU & GPU • Sub-100ms Response  │   100% Private • Zero GPU VRAM       │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

#### Behavioral Specifications:
1. **Interactive States**:
   - Selected card has a highlighted border (`#3b82f6`), dark-blue accent background (`#1e293b`), and active indicator radio bullet.
   - Unselected card has a subtle border (`#334155`), background (`#0f172a`), and muted text (`#94a3b8`).
2. **Conditional Context Disclosure**:
   - When **Groq Cloud** is active:
     - Groq API Key input box is visible and highlighted.
     - "Test Mic & API Connection" button is fully active with live API latency test.
     - Model selection automatically pins to `whisper-large-v3-turbo` with Stage 2 `llama-3.3-70b-versatile`.
   - When **Local CPU** is active:
     - Model selector dropdown (`base`, `small`, `base.en`, `tiny.en`) is visible.
     - Groq API Key input collapses into an optional or disabled state with badge `(Offline Mode Active)`.
     - Connection test button switches to "Test Microphone Level Only".
3. **Data Schema**:
   In `config.json`:
   ```json
   {
       "engine_mode": "groq", // "groq" | "local"
       "language_mode": "hinglish" // "hinglish" | "english" | "auto"
   }
   ```

---

### 3.2 Live "Test Mic & API Connection" Subsystem

#### Functional Requirements:
When clicked, the button simultaneously triggers:
1. **Live Microphone Audio Stream & RMS Level Meter**:
   - Opens non-blocking test stream via `sounddevice` on `selected_device_index`.
   - 30 FPS `QTimer` samples `AudioEngine.get_current_volume()`.
   - Drives a dynamic custom VU level bar with color gradient:
     - Low / Ambient (0.00 – 0.15): Soft green (`#10b981`)
     - Optimal Speaking (0.15 – 0.70): Vibrant emerald / lime (`#22c55e`)
     - High / Clipping (0.70 – 1.00): Warning amber / red (`#ef4444`)
   - Text readout displays live status: e.g., *"Mic Level: Optimal (RMS 0.32) • Realtek High Definition Audio"*.
2. **Groq Cloud API Key & Latency Verification**:
   - Dispatches a background worker thread (`threading.Thread` or `QThread`) to avoid blocking Qt's event loop.
   - Executes HTTP `GET` with `User-Agent: WhisperFlow` and `Authorization: Bearer <key>` to `https://api.groq.com/openai/v1/models` (or lightweight Whisper test payload).
   - Measures exact round-trip ping latency using `time.perf_counter()`.
   - Latency & Status Reporting:
     - **Status 200 (Success)**: Emerald badge `✓ Groq Cloud Connected (Latency: 118ms • whisper-large-v3-turbo ready)`.
     - **Status 401 (Unauthorized)**: Red badge `✗ Invalid Groq API Key (401 Unauthorized)`.
     - **Status 403 / 429**: Amber badge `⚠ Rate Limit / Access Error (HTTP {code})`.
     - **Network Timeout / Offline**: Amber badge `✗ Groq Network Unreachable (Offline Fallback to CPU int8 active)`.
     - **Empty Key**: Information badge `⚠ Enter Groq API key (gsk_...) to test`.
3. **Non-Blocking Test Cycle**:
   - The test runs for 5.0 seconds automatically or until the user clicks "Stop Test".
   - The mic stream closes cleanly upon test completion or dialog dismissal (`closeEvent` / `reject`).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎙️ Microphone & Cloud Diagnostics                                          │
│ ┌────────────────────────────────┐ ┌──────────────────────────────────────┐ │
│ │ [▶ Test Mic & API Connection]  │ │ Status: ● Groq Active (118ms latency)│ │
│ └────────────────────────────────┘ └──────────────────────────────────────┘ │
│ Mic Level: [████████████████░░░░░░░░░░░░░░░░░░░░░░░] 38% Optimal Voice Signal│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.3 Direct Speech Style Selection Cards

#### UI Layout & Structure
Replace the outdated `QComboBox` with a **2×2 Interactive Card Grid** in the Voice & Styles tab:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎭 Speech Style & Formatting Preset                                         │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ 💬 Casual Chat             [✓ Active]│ 💻 Developer Mode                    │
│ Zero punctuation, lowercase natural  │ CamelCase, snake_case, code tokens,  │
│ text, no trailing periods.           │ backticks & git syntax formatting.   │
│ ⚡ 0ms Latency • Zero GPU Passes     │ ⚡ Instant rule-based transforms     │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ 👔 Professional                      │ ✨ Custom Persona                    │
│ Polished executive prose, clean      │ Custom instructions, persona rules   │
│ grammar, formal capitalization.      │ and tone guidelines.                 │
│ ⚡ Standard Executive Prose          │ ⚙️ Custom Prompt Instructions Below  │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

#### Card Specifications:
1. **Interactive Styling**:
   - `QFrame` container with mouse hover & click handlers (`mousePressEvent`).
   - Standard state: `background: #111827; border: 1px solid #334155; border-radius: 8px;`
   - Hover state: `background: #1e293b; border-color: #60a5fa;`
   - Active/Selected state: `background: #172554; border: 2px solid #3b82f6;` with a luminous check badge `[✓ Active]`.
2. **Dynamic Behavior**:
   - Clicking a card immediately marks it as selected, unselects other cards, and updates `self.profile["active_style"]`.
   - If `Custom Persona` is clicked, the custom prompt text area (`QTextEdit`) expands and highlights.
   - When any other card is clicked, the text area remains accessible but dims.
3. **App-Aware Styles Integration**:
   - A toggle below the cards: `[✓] App-Aware Styles (Auto-switch: Developer in IDEs, Casual in Chat apps, Professional in Office)`.

---

### 3.4 Preservation of Sub-50ms Presentation Latency

#### Latency Threat Model & Optimization Strategy
- **Threat 1: Eager Audio Initialization**:
  - Calling `sd.query_devices()` synchronously during `__init__` takes 8–15ms.
  - *Mitigation*: Query devices only once or cache device list; do not start any audio streams during dialog construction.
- **Threat 2: Network / API Calls in `__init__`**:
  - Pinging Groq or Ollama on dialog open would add 200–1500ms and freeze the UI.
  - *Mitigation*: Zero network calls on dialog construction. All connectivity checks must be strictly deferred to user-initiated button clicks and executed on daemon worker threads.
- **Threat 3: Heavy Widget Instantiation**:
  - Constructing hundreds of QWidgets synchronously in `__init__` degraded Round 1 dialog speed to 126ms.
  - *Mitigation*: Maintain the **deferred loading pattern**:
    - Build General Tab (cards + toggle) and Voice Tab (style cards) synchronously (~12ms total).
    - Defer Personal Dictionary tab row population using `QTimer.singleShot(0, self._ensure_dictionary_loaded)`.
- **Benchmark Target**: Mean dialog open latency under **25.0 ms** (far below the 50.0 ms hard threshold).

---

### 3.5 Preservation of 1-Click Dictionary Removal

The in-place removal pattern established in Round 1:
```python
def _on_remove_word_clicked(self, word: str):
    self.profile_mgr.remove_custom_word(word)
    for i in range(self.vocab_list.count()):
        item = self.vocab_list.item(i)
        widget = self.vocab_list.itemWidget(item)
        if widget and getattr(widget, "word", None) == word:
            taken = self.vocab_list.takeItem(i)
            del taken
            break
    self.vocab_count_lbl.setText(f"{len(self.profile_mgr.get_custom_words())} saved")
```
- Benchmark verification confirmed this executes in **0.59 ms**.
- **Rule**: Must NEVER be replaced with `self._refresh_vocab_list()`, which destroys and reallocates all items (costing 15–30ms).

---

## 4. Component Architecture: Floating Capsule Widget Live Status Badges

### 4.1 Visual Geometry & State Design

The floating capsule widget (`ui/floating_widget.py`) operates in two primary visual modes:
1. **Compact Idle Dock**: Always visible on top (when text box has focus or manual show active).
2. **Expanded Active Pill**: 3-segment interactive recording/transcribing bar.

To satisfy Requirement R3 ("show live status badges: e.g., Cloud Active, Local CPU, Hinglish, Transcribing..."), the idle dock geometry and rendering logic are enhanced:

```
┌────────────────────────────────────────────────────────┐
│  | | |   ● Cloud Active   |   HI-EN   |   💬 Casual     │  <- Idle Capsule (148 x 34 px)
└────────────────────────────────────────────────────────┘
```

#### Idle Capsule Badge Layout:
- **Dimensions**: `width: 148px`, `height: 34px`, `corner_radius: 17px`.
- **Segment 1: Voice Emblem**: Minimalist 3-bar animated breathing icon (`| | |`).
- **Segment 2: Engine Status Chip**:
  - `Cloud Active`: Emerald glowing dot (`#10b981`) + text `Cloud` or `Cloud Active` in Segoe UI 11px bold.
  - `Local CPU`: Royal violet dot (`#a855f7`) + text `Local CPU` in Segoe UI 11px bold.
  - `Fallback`: Amber dot (`#f59e0b`) + text `CPU Fallback`.
- **Segment 3: Language Mode Chip**:
  - `Hinglish`: Blue chip badge `Hinglish` or `HI-EN` (`#38bdf8`).
  - `English`: Muted chip badge `EN` (`#94a3b8`).
- **Tooltips & Hover**:
  - Hovering displays high-visibility tooltip: e.g., *"Whisper Flow: Groq Cloud (whisper-large-v3-turbo) • Hinglish Mode • Casual Chat"*.

#### Active Recording & Transcribing Bar Badges:
When user taps the capsule or presses `Ctrl+Shift+Space`:
- **Segment A (Left Circle)**: `[X]` Cancel button (38×38px).
- **Segment B (Middle Pill)**: Live waveform + Sub-status badge:
  - During `STATE_RECORDING`: Real-time audio waveform bars + duration indicator `00:04`.
  - During `STATE_TRANSCRIBING`: Dynamic shimmer pulse + text badge:
    - If Groq: `Stage 1: Groq Cloud...` -> `Stage 2: Hinglish Romanizer...`
    - If Local: `Local CPU int8 Transcribing...`
- **Segment C (Right Circle)**: `[✓]` Done / Submit checkmark (38×38px).

---

### 4.2 State Synchronization Mechanics

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            STATE SYNCHRONIZATION                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   SettingsDialog                       FloatingWidget                       │
│  ┌───────────────────────┐            ┌────────────────────────┐            │
│  │ User changes Engine   │            │ Receives state update  │            │
│  │ (Groq <-> Local)      │──Signal───>│ Repaints badges:       │            │
│  │ User changes Language │            │  ● Cloud Active [HI-EN]│            │
│  │ User selects Style    │            └────────────────────────┘            │
│  └───────────────────────┘                        ▲                         │
│             │                                     │                         │
│             ▼                                     │                         │
│  ┌───────────────────────┐                        │                         │
│  │ App / Config          │────────────────────────┘                         │
│  │ (WhisperFlowApp)      │ (On Failover: Groq Error -> Local Fallback)      │
│  └───────────────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

1. **Signals & Slots**:
   - `SettingsDialog.engine_changed = Signal(str)` (emits `"groq"` or `"local"`).
   - `SettingsDialog.language_changed = Signal(str)` (emits `"hinglish"`, `"english"`, or `"auto"`).
   - `SettingsDialog.style_changed = Signal(str)` (emits active style key).
   - In `app.py`:
     ```python
     self.widget.update_status_badges(
         engine_mode=self.config.get("engine_mode", "groq"),
         language_mode=self.config.get("language_mode", "hinglish"),
         style_mode=self.voice_profile.get_active_style()
     )
     ```
2. **Context Menu Quick Switcher**:
   - Right-clicking the floating capsule exposes direct one-click toggle actions:
     - `Transcription Engine ▸ [✓] Groq Cloud (Sub-100ms) / [ ] Local CPU (int8)`
     - `Language Mode ▸ [✓] Romanized Hinglish (Latin) / [ ] English Only`
     - `Speech Style ▸ [Casual Chat / Developer / Professional / Custom]`
   - Toggling immediately updates the configuration and re-renders widget badges without requiring the full Preferences modal!
3. **Runtime Failover Synchronization**:
   - If Groq API throws a 401, 503, or network timeout during dictation, `whisper_engine.py` catches the error and executes CPU fallback.
   - Concurrently, `WhisperFlowApp` signals `FloatingWidget.set_temporary_badge("CPU Fallback", duration_ms=3000)`, warning the user unobtrusively without modal error popups.

---

## 5. Event Signals & Data Contracts

### 5.1 Signal Dictionary

| Emitter | Signal | Arguments | Receiver | Action |
|---------|--------|-----------|----------|--------|
| `FloatingWidget` | `toggle_recording_requested` | None | `WhisperFlowApp` | Starts or stops audio recording |
| `FloatingWidget` | `cancel_recording_requested` | None | `WhisperFlowApp` | Discards audio, resets to idle (0ms) |
| `FloatingWidget` | `engine_mode_toggled` | `str` (`"groq"`, `"local"`) | `WhisperFlowApp` | Switches active transcription engine |
| `FloatingWidget` | `language_mode_toggled` | `str` (`"hinglish"`, `"english"`) | `WhisperFlowApp` | Switches Romanized Hinglish pipeline |
| `FloatingWidget` | `open_settings_requested` | None | `WhisperFlowApp` | Invokes `open_settings()` (<50ms presentation) |
| `SettingsDialog` | `engine_changed` | `str` | `WhisperFlowApp`, `FloatingWidget` | Synchronizes engine status |
| `SettingsDialog` | `test_connection_requested` | `str` (`api_key`) | `ConnectionTestWorker` | Starts background Groq ping & audio test |
| `ConnectionTestWorker` | `mic_level_updated` | `float` (0.0 to 1.0) | `SettingsDialog` | Updates live VU meter bar |
| `ConnectionTestWorker` | `api_test_completed` | `bool`, `str`, `float` | `SettingsDialog` | Updates latency badge and connection state |

### 5.2 Configuration Data Contract (`config.json`)

```json
{
    "engine_mode": "groq",
    "model_name": "base",
    "device": "cpu",
    "compute_type": "int8",
    "groq_api_key": "gsk_...",
    "language_mode": "hinglish",
    "paste_mode": "instant_paste",
    "global_hotkey": "ctrl+shift+space",
    "sound_effects": false,
    "window_x": 1720,
    "window_y": 1020,
    "input_device_index": null,
    "auto_show_on_textbox": true
}
```

---

## 6. Implementation Architecture & Drop-in Component Designs

### 6.1 `EngineSelectorWidget` (General Tab)

```python
class EngineSelectorWidget(QWidget):
    """Modern segmented visual cards for Groq Cloud vs Local CPU selection."""
    engine_changed = Signal(str)

    def __init__(self, current_engine="groq", parent=None):
        super().__init__(parent)
        self.current_engine = current_engine
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Card 1: Groq Cloud
        self.card_groq = self._create_card(
            engine_id="groq",
            title="Groq Cloud Engine",
            badge="Ultra-Fast whisper-large-v3-turbo",
            desc="0% CPU & GPU load • Sub-100ms response time • High accuracy",
            is_active=(current_engine == "groq")
        )
        layout.addWidget(self.card_groq)

        # Card 2: Local CPU
        self.card_local = self._create_card(
            engine_id="local",
            title="Local CPU Engine",
            badge="int8 Offline (CTranslate2)",
            desc="100% Offline & Private • Zero GPU VRAM • 6 CPU threads",
            is_active=(current_engine == "local")
        )
        layout.addWidget(self.card_local)

    def _create_card(self, engine_id, title, badge, desc, is_active):
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setProperty("engine_id", engine_id)
        card.setProperty("active", is_active)
        
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 12, 14, 12)
        c_layout.setSpacing(4)

        header_row = QHBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")
        header_row.addWidget(t_lbl)
        header_row.addStretch()

        radio = QLabel("●" if is_active else "○")
        radio.setStyleSheet("color: #3b82f6; font-size: 16px;" if is_active else "color: #64748b; font-size: 16px;")
        radio.setObjectName("radio_indicator")
        header_row.addWidget(radio)
        c_layout.addLayout(header_row)

        b_lbl = QLabel(badge)
        b_lbl.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600;")
        c_layout.addWidget(b_lbl)

        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        d_lbl.setWordWrap(True)
        c_layout.addWidget(d_lbl)

        self._apply_card_style(card, is_active)
        card.mousePressEvent = lambda e: self._on_card_clicked(engine_id)
        return card

    def _apply_card_style(self, card, is_active):
        if is_active:
            card.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border: 2px solid #3b82f6;
                    border-radius: 8px;
                }
            """)
        else:
            card.setStyleSheet("""
                QFrame {
                    background-color: #0f172a;
                    border: 1px solid #334155;
                    border-radius: 8px;
                }
                QFrame:hover {
                    border-color: #64748b;
                    background-color: #161e2e;
                }
            """)

    def _on_card_clicked(self, engine_id):
        if self.current_engine == engine_id:
            return
        self.current_engine = engine_id
        self._apply_card_style(self.card_groq, engine_id == "groq")
        self._apply_card_style(self.card_local, engine_id == "local")
        self.card_groq.findChild(QLabel, "radio_indicator").setText("●" if engine_id == "groq" else "○")
        self.card_local.findChild(QLabel, "radio_indicator").setText("●" if engine_id == "local" else "○")
        self.engine_changed.emit(engine_id)
```

---

### 6.2 `StyleCardGridWidget` (Voice & Styles Tab)

```python
class StyleCardGridWidget(QWidget):
    """Direct 2x2 clickable cards for Casual Chat, Developer, Professional, and Custom."""
    style_selected = Signal(str)

    STYLES = [
        ("casual", "Casual Chat", "Zero formal punctuation, lowercase text, no periods. Ideal for Slack & Discord.", "⚡ 0ms Latency • Zero GPU"),
        ("code", "Developer Mode", "CamelCase, snake_case, code syntax, backticks, git commit conventions.", "⚡ Instant rule-based transforms"),
        ("professional", "Professional", "Polished executive prose, clean grammar, formal capitalization.", "⚡ Standard Executive Prose"),
        ("custom", "Custom Persona", "Applies your personalized prompt instructions and formatting guidelines.", "⚙️ Configurable Prompt Below")
    ]

    def __init__(self, current_style="professional", parent=None):
        super().__init__(parent)
        self.current_style = current_style
        self.cards = {}

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)

        for idx, (key, title, desc, tag) in enumerate(self.STYLES):
            row = idx // 2
            col = idx % 2
            card = self._build_card(key, title, desc, tag, is_active=(key == current_style))
            grid.addWidget(card, row, col)
            self.cards[key] = card

    def _build_card(self, key, title, desc, tag, is_active):
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        h_row = QHBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #f8fafc;")
        h_row.addWidget(t_lbl)
        h_row.addStretch()

        badge = QLabel("✓ Active" if is_active else "")
        badge.setObjectName("active_badge")
        badge.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold;")
        h_row.addWidget(badge)
        layout.addLayout(h_row)

        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        d_lbl.setWordWrap(True)
        layout.addWidget(d_lbl)

        tag_lbl = QLabel(tag)
        tag_lbl.setStyleSheet("color: #34d399; font-size: 10px; font-weight: 600;")
        layout.addWidget(tag_lbl)

        self._set_style(card, is_active)
        card.mousePressEvent = lambda e, k=key: self._on_select(k)
        return card

    def _set_style(self, card, is_active):
        if is_active:
            card.setStyleSheet("QFrame { background-color: #1e293b; border: 2px solid #3b82f6; border-radius: 8px; }")
        else:
            card.setStyleSheet("QFrame { background-color: #0b0f19; border: 1px solid #334155; border-radius: 8px; } QFrame:hover { border-color: #64748b; }")

    def _on_select(self, key):
        if self.current_style == key:
            return
        self.current_style = key
        for k, card in self.cards.items():
            active = (k == key)
            self._set_style(card, active)
            card.findChild(QLabel, "active_badge").setText("✓ Active" if active else "")
        self.style_selected.emit(key)
```

---

### 6.3 `LiveMicAndApiTestWidget` (Real-Time Diagnostics)

```python
class LiveMicAndApiTestWidget(QWidget):
    """Live microphone audio level meter and Groq API latency testing widget."""
    def __init__(self, config, audio_engine, parent=None):
        super().__init__(parent)
        self.config = config
        self.audio_engine = audio_engine
        self.is_testing = False
        self.test_stream = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Top Button & Status row
        top_row = QHBoxLayout()
        self.test_btn = QPushButton("Test Mic & API Connection")
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.clicked.connect(self.toggle_test)
        top_row.addWidget(self.test_btn)

        self.api_status_lbl = QLabel("Groq API: Not tested")
        self.api_status_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        top_row.addWidget(self.api_status_lbl)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Live VU Meter Bar
        meter_row = QHBoxLayout()
        meter_lbl = QLabel("Mic Level:")
        meter_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        meter_row.addWidget(meter_lbl)

        self.meter_bar = QProgressBar()
        self.meter_bar.setRange(0, 100)
        self.meter_bar.setValue(0)
        self.meter_bar.setTextVisible(False)
        self.meter_bar.setFixedHeight(10)
        self.meter_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0b0f19;
                border: 1px solid #334155;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:0.7 #3b82f6, stop:1.0 #ef4444);
                border-radius: 4px;
            }
        """)
        meter_row.addWidget(self.meter_bar)

        self.level_val_lbl = QLabel("0%")
        self.level_val_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; min-width: 35px;")
        meter_row.addWidget(self.level_val_lbl)
        layout.addLayout(meter_row)

        # Update timer for RMS VU meter (33ms = ~30 FPS)
        self.vu_timer = QTimer(self)
        self.vu_timer.timeout.connect(self._update_vu_meter)

    def toggle_test(self):
        if self.is_testing:
            self.stop_test()
        else:
            self.start_test()

    def start_test(self):
        self.is_testing = True
        self.test_btn.setText("Stop Test")
        self.api_status_lbl.setText("Testing Groq latency & mic...")
        self.api_status_lbl.setStyleSheet("color: #38bdf8; font-size: 12px;")

        # Start non-blocking sounddevice test stream if audio engine is not actively recording
        if not self.audio_engine.is_recording:
            try:
                self.audio_engine.start_recording()
            except Exception as e:
                self.api_status_lbl.setText(f"Mic error: {e}")
        self.vu_timer.start(33)

        # Concurrently test Groq API in worker thread
        threading.Thread(target=self._test_groq_api_worker, daemon=True).start()

    def stop_test(self):
        self.is_testing = False
        self.test_btn.setText("Test Mic & API Connection")
        self.vu_timer.stop()
        if self.audio_engine.is_recording:
            self.audio_engine.stop_recording()
        self.meter_bar.setValue(0)
        self.level_val_lbl.setText("0%")

    def _update_vu_meter(self):
        vol = self.audio_engine.get_current_volume()  # 0.0 to 1.0
        pct = int(min(1.0, vol) * 100)
        self.meter_bar.setValue(pct)
        self.level_val_lbl.setText(f"{pct}%")

    def _test_groq_api_worker(self):
        import time, urllib.request, json
        key = self.config.get("groq_api_key", "").strip()
        if not key:
            QTimer.singleShot(0, lambda: self._on_groq_result(False, "No Groq API key set", 0.0))
            return

        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {key}", "User-Agent": "WhisperFlow"}
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                elapsed = (time.perf_counter() - t0) * 1000.0
                if resp.status == 200:
                    QTimer.singleShot(0, lambda: self._on_groq_result(True, f"Groq Online ({elapsed:.0f}ms)", elapsed))
                else:
                    QTimer.singleShot(0, lambda: self._on_groq_result(False, f"HTTP {resp.status}", elapsed))
        except urllib.error.HTTPError as he:
            elapsed = (time.perf_counter() - t0) * 1000.0
            msg = "401 Invalid Key" if he.code == 401 else f"HTTP {he.code}"
            QTimer.singleShot(0, lambda: self._on_groq_result(False, msg, elapsed))
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000.0
            QTimer.singleShot(0, lambda: self._on_groq_result(False, f"Offline ({e.__class__.__name__})", elapsed))

    def _on_groq_result(self, success, message, latency):
        if success:
            self.api_status_lbl.setText(f"✓ {message}")
            self.api_status_lbl.setStyleSheet("color: #34d399; font-weight: bold; font-size: 12px;")
        else:
            self.api_status_lbl.setText(f"✗ {message}")
            self.api_status_lbl.setStyleSheet("color: #f87171; font-weight: bold; font-size: 12px;")
```

---

### 6.4 `FloatingWidget` Live Status Badges & Paint Enhancements

In `ui/floating_widget.py`, extend `FloatingWidget` with:
- Attributes: `self.engine_mode = "groq"`, `self.language_mode = "hinglish"`, `self.active_style = "casual"`.
- Geometry: Idle dock width expanded from 56px to 148px (`self.dock_w = 148`).
- Paint logic for idle dock:
  1. Background obsidian pill with violet rim glow.
  2. Left: 3-bar animated voice emblem (`| | |`).
  3. Center badge:
     - If `engine_mode == "groq"`: Draws glowing green dot (`#10b981`) + text `Cloud` (or `Cloud Active`).
     - If `engine_mode == "local"`: Draws violet dot (`#a855f7`) + text `Local CPU`.
  4. Right badge:
     - If `language_mode == "hinglish"`: Draws rounded sapphire chip `HI-EN` or `Hinglish`.
     - If `language_mode == "english"`: Draws muted chip `EN`.
- Seamless State Transitions:
  - Transition from 148px idle dock to 188px recording bar preserves center-anchored positioning (`move(cx - new_w // 2, cy - new_h // 2)`).
  - During `STATE_TRANSCRIBING`: The middle pill renders dynamic shimmer and text: `Transcribing... (Groq Cloud)` or `Transcribing... (CPU int8)`.

---

## 7. Verification Strategy & Acceptance Criteria Traceability

| Acceptance Criteria | Target | Verification Method | Automated Test Module |
|---------------------|--------|---------------------|-----------------------|
| **Preferences Dialog Open Latency** | < 50.0 ms | Benchmark 5 consecutive instantiations with `time.perf_counter()` | `tests/test_ui_responsiveness.py` (`test_ac2_preferences_dialog_open_latency`) |
| **Engine Selector Toggle** | Immediate switch | Click toggle cards, verify `config["engine_mode"]` updates, signals emit | New test in `tests/test_ui_responsiveness.py` |
| **Live Mic & API Connection Test** | Non-blocking, <4s timeout | Simulate click, verify VU timer starts, verify thread emits latency signal | New test in `tests/test_ui_responsiveness.py` |
| **Style Selection Cards** | 4 clickable cards | Verify selecting card sets `active_style` and highlights border | New test in `tests/test_ui_responsiveness.py` |
| **1-Click Dictionary Removal** | < 50.0 ms (< 1ms target) | `_on_remove_word_clicked` and `_on_remove_rep_clicked` via `takeItem(i)` | `tests/test_ui_responsiveness.py` (`test_1_click_instant_dictionary_removal`) |
| **Floating Capsule Status Badges** | Repaint & state sync | Verify badges update on `update_status_badges("groq", "hinglish")` | New test in `tests/test_ui_responsiveness.py` |
| **All Existing Automated Tests** | 100% pass | Discover and execute all tests via `.venv\Scripts\python.exe -m unittest discover tests` | Entire `tests/` directory |

---

## 8. Summary of Proposed File Modifications

1. `config.py`: Add `"engine_mode": "groq"` and `"language_mode": "hinglish"` to `DEFAULT_CONFIG`.
2. `ui/settings_dialog.py`:
   - Integrate `EngineSelectorWidget` in General Tab.
   - Integrate `LiveMicAndApiTestWidget` in General Tab.
   - Replace style combo box with `StyleCardGridWidget` in Voice & Styles Tab.
   - Retain deferred dictionary population and 1-click in-place `takeItem(i)` deletion.
3. `ui/floating_widget.py`:
   - Expand idle dock geometry (`dock_w = 148px`).
   - Add status chip rendering in `paintEvent` for engine (`Cloud Active` / `Local CPU`) and language (`Hinglish` / `EN`).
   - Add `update_status_badges(engine, language, style)` slot.
4. `app.py`:
   - Wire `SettingsDialog.engine_changed` to update `FloatingWidget` and `WhisperEngine`.
   - Update tray context menu with direct Engine and Language switches.
5. `tests/test_ui_responsiveness.py`:
   - Add test coverage for `EngineSelectorWidget`, `LiveMicAndApiTestWidget`, `StyleCardGridWidget`, and `FloatingWidget` badge rendering.
