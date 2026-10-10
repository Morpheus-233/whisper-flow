# Whisper Flow 🎙️✨

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg)](https://microsoft.com/windows)
[![Engine: faster--whisper](https://img.shields.io/badge/Engine-faster--whisper%20(CTranslate2)-orange.svg)](https://github.com/SYSTRAN/faster-whisper)

A minimalist, GPU-accelerated local voice-to-text dictation application for Windows featuring a modern floating widget inspired by Wispr Flow.

Whisper Flow stays invisible until you focus an editable text box in **any application**, dynamically expands into an interactive audio soundwave recording bar, transcribes your speech completely offline with high accuracy, and pastes the result directly into your active field.

---

## ✨ Features

- 🎯 **Intelligent Text Box Focus Detection**:
  - Automatically appears when you click into an editable text field (Chrome, Edge, Spotify search, PowerPoint text boxes/notes, Slack, Discord, VS Code, Word, Notepad, etc.).
  - Automatically hides when clicking outside, switching to non-text UI, or focusing read-only / password inputs.
  - Can be toggled to stay visible 24/7 if preferred.

- 💎 **Dual-State Wispr Flow Widget**:
  - **Resting Squircle Dock**: Sleek obsidian pill with a subtle violet audio aura.
  - **Dynamic 3-Segment Recording Bar**:
    - **`[ ✕ ]` Cancel**: Discards current audio and collapses back without quitting.
    - **`[ • • |||| • • ]` Waveform**: Real-time soundwave visualization reactive to microphone input volume.
    - **`[ ✓ ]` Finish**: Transcribes speech, flashes green, and types text directly into the active field.

- ⚡ **Ultra-Fast Local Transcription (`faster-whisper`)**:
  - Runs 100% locally on your machine with **zero telemetry or cloud calls**.
  - **Hardware Auto-Detection**: Leverages NVIDIA CUDA (`float16`) if supported, with automatic fallback to high-speed CPU inference (`int8`).
  - Dynamic model download on first run (default: `base.en`).

- 🧹 **Automatic Speech Cleaning**:
  - Automatically removes stutters, repeated filler phrases, and false starts.
  - Formats punctuation and capitalization cleanly.

- 💻 **Terminal & Developer Friendly**:
  - Native support for modern terminal emulators (Windows Terminal, OpenCode, PowerShell, Git Bash, WezTerm, Alacritty) with automated clipboard injection (`Ctrl+Shift+V`).

- 🖥️ **Multi-Monitor Aware**:
  - Remembers user placement on multi-monitor setups without jumping across screens on clicks.

---

## 🚀 Quick Start

### Option 1: Run from Source (Python)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Morpheus-233/whisper-flow.git
   cd whisper-flow
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Enable NVIDIA GPU Acceleration:**
   If you have an NVIDIA GPU (RTX / GTX) and want maximum speed with CUDA:
   ```bash
   pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
   ```

5. **Launch the application:**
   - Run via terminal:
     ```bash
     python app.py
     ```
   - Or double-click `run_app.bat` (Console launcher)
   - Or double-click `WhisperFlow_Silent.vbs` (Silent background launcher)

---

### Option 2: Pre-Built Portable Executable

Download the latest `WhisperFlow-windows-x64.zip` from the [GitHub Releases](https://github.com/Morpheus-233/whisper-flow/releases) page. Extract and run `WhisperFlow.exe` without needing Python installed.

---

## 🎮 How to Use

1. Click into any editable text box or terminal prompt.
2. Click the **Whisper Flow widget** or press **`Ctrl + Shift + Space`** to start recording.
3. Speak naturally. The soundwave bars will dance to your voice volume.
4. When finished:
   - Click **`[ ✓ ]`** (or press **`Ctrl + Shift + Space`**) to transcribe and auto-paste directly into your field.
   - Click **`[ ✕ ]`** to discard the recording.

---

## ⚙️ Configuration & Settings

Access settings by right-clicking the system tray icon or pressing the gear icon on the widget:
- **Model Selection**: Choose between `tiny.en`, `base.en`, `small.en`, `medium.en`, or multilingual models.
- **Microphone Selection**: Choose your preferred input device.
- **Global Hotkey**: Customize the global activation shortcut (default: `Ctrl + Shift + Space`).
- **Show Only In Text Boxes**: Toggle between context-aware appearance or persistent dock.

Settings are saved locally in `config.json`.

---

## 🛠️ Project Structure

```text
whisper-flow/
├── ui/
│   ├── floating_widget.py     # Wispr Flow dual-state widget & animations
│   ├── settings_dialog.py     # Preferences dialog
│   └── __init__.py
├── app.py                     # Main application entry point & tray icon
├── audio_engine.py            # Audio recording & sounddevice stream
├── config.py                  # User settings manager
├── focus_detector.py          # Windows UI Automation text-box focus tracking
├── paster.py                  # Smart text pasting (Win32 & terminal aware)
├── speech_detector.py         # Voice activity detection (VAD)
├── text_cleaner.py            # Stutter and duplicate cleanup
├── whisper_engine.py          # faster-whisper CTranslate2 transcription engine
├── WhisperFlow_Silent.vbs     # Silent background launcher
├── run_app.bat                # Windows batch launcher
├── create_desktop_shortcut.py # Desktop shortcut generator
├── requirements.txt           # Python package dependencies
└── README.md
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
