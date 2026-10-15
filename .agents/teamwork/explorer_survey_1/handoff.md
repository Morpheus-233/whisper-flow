# Survey Explorer 1: Codebase Architecture & Survey Report

## 1. Observation

### 1.1 Environment & System Baseline
- **OS**: Windows 10 Pro (22H2) x86_64 (`WIN32_NT 10.0.19045.6466`)
- **CPU**: 12th Gen Intel(R) Core(TM) i5-12400F (12 threads)
- **GPU**: NVIDIA GeForce RTX 3060 (12 GB VRAM)
- **Python Runtimes**:
  - System Python: `Python 3.12.2` at `C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe` (lacks `PySide6`).
  - Virtual Environment: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.venv\Scripts\python.exe` (Python 3.12.2). Verified working packages: `PySide6==6.11.2`, `faster-whisper==1.2.1`, `ctranslate2==4.8.1`, `sounddevice==0.5.6`, `scipy==1.18.1`, `numpy==2.5.3`, `pyautogui==0.9.54`, `pyperclip==1.11.0`, `pygetwindow==0.0.9`, `uiautomation==2.0.29`, `torch==2.12.0`, `pytest==9.1.1`.

### 1.2 Repository Structure & File Catalog
Directory listing of `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow`:
- **Root Modules**:
  - `app.py` (27,660 bytes, 692 lines): Main application lifecycle, single-instance mutex check, IPC server (`QLocalServer`), system tray, global hotkey listeners (`Ctrl+Shift+Space`, `Ctrl+Alt+Space`), mouse listener, visibility debouncing, paste triggering.
  - `whisper_engine.py` (12,410 bytes, 296 lines): `WhisperEngine` singleton. Supports CPU `int8` (`cpu_threads=6`, 0 MB VRAM) and CUDA (`float16`). Implements Groq Whisper API cloud fallback (`whisper-large-v3-turbo` at `https://api.groq.com/openai/v1/audio/transcriptions`). Supports `initial_prompt` biasing.
  - `voice_profile.py` (6,113 bytes, 181 lines): `VoiceProfileManager` singleton managing `voice_profile.json`. Implements `get_custom_words()`, `add_custom_word()`, `remove_custom_word()`, `get_replacements()`, `add_replacement()`, `remove_replacement()`, `get_initial_prompt()`, and regex-based `apply_replacements()`.
  - `voice_profile.json` (2,510 bytes, 97 lines): User profile containing 27 custom words, 14 phonetic word replacements, style configuration, acoustic settings, and app-aware styling rules.
  - `style_engine.py` (6,886 bytes, 168 lines): `StyleEngine` coordinating style transformations (`professional`, `casual`, `code`, `raw`, `custom`). Dispatches `casual` to `format_casual_chat`. Dispatches others to Ollama API (`http://127.0.0.1:11434`) if enabled.
  - `text_cleaner.py` (4,733 bytes, 127 lines): Rule-based speech cleaner (`clean_speech_text`) and casual chat formatter (`format_casual_chat`). Removes vocal fillers, stutters, trailing punctuation, formal commas, and title casing while protecting URLs and code/number tokens.
  - `audio_engine.py` (3,919 bytes, 116 lines): Sounddevice-based 16kHz mono audio recorder. RMS volume calculation and sliding window audio chunk retention.
  - `focus_detector.py` (17,750 bytes, 435 lines): `FocusDetector` utilizing `uiautomation` and COM `IUIAutomationFocusChangedEventHandler` to monitor active control focus changes, plus native Win32 `GUITHREADINFO` caret checks.
  - `paster.py` (4,555 bytes, 127 lines): `Paster` using `pyperclip` and synthetic Windows keyboard events (`keybd_event`) for `Ctrl+V` and terminal `Ctrl+Shift+V` (e.g. WezTerm, Alacritty) with `AttachThreadInput` focus restoration.
  - `config.py` (1,105 bytes, 38 lines) & `config.json` (340 bytes, 13 lines): Application configuration manager.
  - `studio_server.py` (14,962 bytes, 393 lines): HTTP server (port 8000) for Web Voice Studio. Implements `compute_diff`, `audio_bytes_to_float32`, API endpoints `/api/sentences`, `/api/profile`, `/api/transcribe`, `/api/add_word`.
  - `create_desktop_shortcut.py` (1,155 bytes, 34 lines): Creates `Whisper Flow.lnk` on Windows Desktop pointing to `WhisperFlow_Silent.vbs`.
  - `WhisperFlow_Silent.vbs` (390 bytes, 12 lines): VBScript running `.venv\Scripts\pythonw.exe app.py` without a console window.
  - `run_app.bat` (218 bytes, 11 lines): Batch file launching `app.py` via virtualenv.
  - `requirements.txt` (178 bytes, 11 lines): Dependencies list.
- **Subdirectories**:
  - `data/calibration_sentences.json` (24,115 bytes, 981 lines): 100 sentences (verified: exactly 50 `"english"` and 50 `"hindi_hinglish"`).
  - `ui/floating_widget.py` (18,970 bytes, 448 lines): Frameless, always-on-top, `WS_EX_NOACTIVATE` widget with resting dock and 3-segment recording pill bar.
  - `ui/settings_dialog.py` (27,103 bytes, 701 lines): Tabbed preferences dialog (General, Voice & Styles, Personal Dictionary).
  - `ui/voice_training_dialog.py` (15,024 bytes, 393 lines): Voice training wizard dialog (noise calibration and speech cadence).
  - `ui/theme_helper.py` (1,557 bytes, 43 lines): Native Windows DWM immersive dark mode helper (`DWMWA_USE_IMMERSIVE_DARK_MODE`).
  - `studio/index.html` (58,919 bytes): Frontend SPA for Web Voice Studio.
  - `scratch/`: 15 ad-hoc test scripts for caret detection, focus, and UIA inspection.

### 1.3 Direct Command Executions & Diagnostic Findings
1. **Test Discovery Tool**:
   - Command: `.\.venv\Scripts\python.exe -m unittest discover tests`
   - Result:
     ```
     ImportError: Start directory is not importable: 'tests'
     ```
   - Direct Observation: The directory `tests` does not exist in the project root.

2. **Second-Instance Startup & Mutex Exit Timing**:
   - Command: Mutex check test running `subprocess.run(['.\\.venv\\Scripts\\python.exe', 'app.py'])` when `Local\WhisperFlow_SingleInstance_Mutex_v3` is held.
   - Result: Exited cleanly with returncode `0`, but elapsed time was `970.2 ms`.
   - Reason: `app.py` lines 42-60 import `PySide6`, `faster_whisper`, `ctranslate2`, `torch`, `scipy`, `sounddevice`, `uiautomation` before executing `main()` and checking the mutex at line 610!
   - Baseline Raw Python Startup: `.\.venv\Scripts\python.exe -c "import sys; sys.exit(0)"` takes `45.3 ms`.

3. **Dialog Instantiation Latencies**:
   - Command: Instantiated `VoiceTrainingDialog` and `SettingsDialog` in headless harness.
   - Result:
     - `VoiceTrainingDialog init`: `24.50 ms` (< 50ms requirement met).
     - `SettingsDialog init`: `126.43 ms` (> 50ms requirement; failed due to synchronously instantiating 41 composite row widgets: 27 custom words and 14 replacement rows in `_create_dictionary_tab`).

4. **Dictionary 1-Click Removal Latency**:
   - Command: Benchmarked `SettingsDialog._on_remove_word_clicked('Soham')`.
   - Result: `16.00 ms` (< 20ms, non-blocking UI update).

5. **Calibration Sentences Dataset**:
   - Command: Verified sentence counts in `data/calibration_sentences.json`.
   - Result: Total: 100 sentences. `Counter({'english': 50, 'hindi_hinglish': 50})`.
   - Discrepancy: `ui/voice_training_dialog.py` lines 15-19 has a hardcoded array `CALIBRATION_SENTENCES` with only 3 English sentences, failing to load or utilize `data/calibration_sentences.json`.

6. **Style Transformations**:
   - Casual Style: Verified `format_casual_chat("Hello, world! We are testing Whisper Flow.")` -> `"hello world we are testing whisper flow"`. Trailing punctuation and formal commas removed with zero GPU passes.
   - Developer Mode: `style_engine.py` line 108: `if not profile.get("ollama_enabled", False): return cleaned_base`. No rule-based camelCase, snake_case, or code syntax transformations implemented.
   - Custom Persona: `style_engine.py` line 108: relies on Ollama; returns untransformed base if Ollama is disabled.

---

## 2. Logic Chain

1. **Test Infrastructure**:
   - *Observation*: Running `python -m unittest discover tests` returns `ImportError: Start directory is not importable: 'tests'`.
   - *Deduction*: There are no automated unit or integration tests registered under `tests/`. All acceptance criteria currently rely on manual verification.
   - *Conclusion*: A comprehensive, automated test suite must be placed in `tests/` matching `unittest` discovery conventions.

2. **Single-Instance IPC & Sub-100ms Exit**:
   - *Observation*: A second instance takes `970.2 ms` to exit upon encountering an existing mutex. Meanwhile, bare Python process startup takes `45.3 ms`.
   - *Deduction*: `app.py` lines 42-60 import heavy native binary extensions (`PySide6`, `faster_whisper`, `ctranslate2`, `torch`, `uiautomation`) at module scope before `main()` executes the mutex check at line 610.
   - *Conclusion*: Moving the single-instance mutex check to the top of `app.py` (before importing `PySide6` or `faster_whisper`) will allow the second instance to call `AllowSetForegroundWindow`, broadcast the show event, and terminate within ~50ms (< 100ms requirement).

3. **Settings Dialog Open Latency**:
   - *Observation*: `SettingsDialog` takes `126.43 ms` to initialize, whereas `VoiceTrainingDialog` takes `24.50 ms`.
   - *Deduction*: `SettingsDialog.__init__` eagerly populates the `Personal Dictionary` tab by instantiating 41 custom `QWidget` row objects (`WordRowWidget` and `ReplacementRowWidget`), each constructing layouts, buttons, and style sheets.
   - *Conclusion*: Deferring the row population until the tab is displayed or initializing row widgets lazily will bring `SettingsDialog` startup under `50ms`.

4. **Bilingual Calibration & Automated Diffing**:
   - *Observation*: `data/calibration_sentences.json` contains 100 bilingual sentences (50 English, 50 Hindi/Hinglish). `studio_server.py` implements `compute_diff` with word-level alignment, accuracy calculation, and misheard pair extraction. However, `ui/voice_training_dialog.py` only contains 3 hardcoded sentences and does not compute diffs or map misheard words.
   - *Deduction*: The desktop GUI voice training wizard is decoupled from the 100-sentence dataset and the diff computation logic present in `studio_server.py`. Moreover, `studio_server.py` loads `WhisperEngine` upon module import, making it unsuitable for importing `compute_diff` without side effects.
   - *Conclusion*: Refactoring `compute_diff` into a standalone, pure module (e.g. `calibration_engine.py` or `speech_calibration.py`) will allow both `ui/voice_training_dialog.py` and `studio_server.py` to share the 100-sentence dataset, compute diffs, and auto-register phonetic replacements into `voice_profile.json`.

5. **Instant Rule-Based Speech Styling**:
   - *Observation*: `format_casual_chat` in `text_cleaner.py` correctly handles Casual Chat without LLMs. However, Developer Mode and Custom Persona in `style_engine.py` fall back directly to `cleaned_base` when Ollama is disabled or unreachable.
   - *Deduction*: The requirements specify instant rule-based speech transformations for Developer Mode (spoken syntax to camelCase, snake_case, code tokens) and Custom Persona without adding latency or requiring GPU LLMs.
   - *Conclusion*: Dedicated rule-based transformation functions for Developer Mode and Custom Persona must be implemented in `text_cleaner.py` / `style_engine.py` to fulfill R2.

---

## 3. Caveats

1. **Ollama Daemon**: Ollama is optional and was not running during this survey. Local LLM styling was evaluated based on the code's fallback paths.
2. **Microphone Device**: Headless/automated test execution does not require a physical microphone if audio arrays are synthetic or pre-recorded; however, real live dictation requires an active sound recording device.
3. **GPU VRAM in CPU Mode**: In CPU mode (`device="cpu", compute_type="int8"`), faster-whisper consumes 0 MB of GPU VRAM, verified by checking process GPU memory allocations.

---

## 4. Conclusion

Whisper Flow has a robust foundational architecture:
- Hardware-efficient `faster-whisper` CPU `int8` engine and Groq API fallback exist in `whisper_engine.py`.
- `data/calibration_sentences.json` contains the required 100 bilingual sentences.
- Win32 single-instance mutex and IPC server exist in `app.py`.
- Modern floating widget and dark mode theme helpers exist in `ui/`.

However, the following key gaps must be addressed to fulfill all requirements and acceptance criteria:
1. **Create `tests/` Suite**: Implement complete unittest suite discoverable via `python -m unittest discover tests`.
2. **Optimize `app.py` Single-Instance Mutex Check**: Move the mutex check ahead of heavy module imports so secondary instance launches exit in <100ms.
3. **Optimize `SettingsDialog` Creation**: Defer dictionary widget generation to achieve <50ms dialog open latency.
4. **Integrate 100-Sentence Dataset & Diffing in Voice Training Dialog**: Extract diffing into a modular engine, load 100 sentences in `VoiceTrainingDialog`, and support automated misheard phonetic rule registration.
5. **Implement Rule-Based Developer Mode & Custom Persona**: Add rule-based speech transformation for camelCase, snake_case, and code syntax without GPU/LLM dependencies.

---

## 5. Verification Method

To independently verify all observations in this report:

1. **Verify Python Virtual Environment & Dependencies**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import PySide6, faster_whisper, ctranslate2, sounddevice, scipy; print('All core libraries loaded successfully')"
   ```

2. **Verify Missing Test Directory**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover tests
   ```
   *(Expected error: `ImportError: Start directory is not importable: 'tests'`)*

3. **Verify Calibration Sentences Count & Categories**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import json, collections; d = json.load(open('data/calibration_sentences.json', encoding='utf-8')); print(len(d), collections.Counter(x['category'] for x in d))"
   ```
   *(Expected output: `100 Counter({'english': 50, 'hindi_hinglish': 50})`)*

4. **Verify Dialog Instantiation Latency**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import sys, time; from PySide6.QtWidgets import QApplication; app = QApplication(sys.argv); from config import load_config; from audio_engine import AudioEngine; from whisper_engine import WhisperEngine; cfg = load_config(); ae = AudioEngine(); we = WhisperEngine.get_instance(); from ui.settings_dialog import SettingsDialog; t0 = time.time(); dlg = SettingsDialog(cfg, ae, we); print(f'SettingsDialog: {(time.time()-t0)*1000:.1f}ms'); from ui.voice_training_dialog import VoiceTrainingDialog; t0 = time.time(); dlg2 = VoiceTrainingDialog(ae, we); print(f'VoiceTrainingDialog: {(time.time()-t0)*1000:.1f}ms')"
   ```

5. **Verify Secondary Instance Exit Latency with Active Mutex**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import ctypes, subprocess, time; kernel32 = ctypes.windll.kernel32; m = kernel32.CreateMutexW(None, False, 'Local\\WhisperFlow_SingleInstance_Mutex_v3'); t0 = time.time(); subprocess.run(['.\\.venv\\Scripts\\python.exe', 'app.py']); print(f'Exited in: {(time.time()-t0)*1000:.1f}ms'); kernel32.CloseHandle(m)"
   ```
