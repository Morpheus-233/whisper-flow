# Whisper Flow

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg)](https://microsoft.com/windows)
[![Engine: faster-whisper](https://img.shields.io/badge/Engine-faster--whisper%20(CTranslate2)-orange.svg)](https://github.com/SYSTRAN/faster-whisper)

A minimalist, GPU-accelerated local voice-to-text dictation application for Windows featuring an expandable floating widget inspired by Wispr Flow.

Whisper Flow remains hidden until you focus an editable text input in any application, expands into an interactive recording bar with live soundwave visualization, transcribes speech completely offline with high accuracy, and pastes the result directly into your active input field.

---

## Features

- **Intelligent Text Box Focus Detection**:
  - Automatically appears when an editable text field is focused (Chrome, Edge, Spotify search, PowerPoint text boxes/notes pane, Slack, Discord, VS Code, Word, Notepad, etc.).
  - Automatically hides when clicking outside, switching to non-text UI, or focusing read-only / password inputs.
  - Can be toggled to stay visible continuously via settings or tray menu.

- **Dual-State Widget**:
  - **Resting Dock**: Compact obsidian capsule with an audio indicator glow.
  - **Dynamic 3-Segment Recording Bar**:
    - **Cancel Button**: Discards the current audio and collapses back without exiting.
    - **Waveform Capsule**: Real-time soundwave visualization reactive to microphone volume.
    - **Finish Button**: Transcribes speech, displays confirmation, and types text directly into the active field.

- **Fast Local Transcription (faster-whisper)**:
  - Runs 100% locally on your machine with zero cloud requests or telemetry.
  - **Hardware Auto-Detection**: Automatically utilizes NVIDIA CUDA (float16) when supported, with seamless fallback to fast CPU inference (int8).
  - Dynamic model downloading on first launch (default: `base.en`).

- **Speech Post-Processing**:
  - Automatically cleans false starts, repeated words, and common transcription artifacts.
  - Applies capitalization and punctuation rules.

- **Terminal and Developer Support**:
  - Native support for modern terminal emulators (Windows Terminal, OpenCode, PowerShell, Git Bash, WezTerm, Alacritty) with automated clipboard injection (`Ctrl+Shift+V`).

- **Multi-Monitor Aware**:
  - Maintains user-defined position across multi-monitor setups without jumping across screens on clicks.

---

## Quick Start

### Option 1: Run from Source (Python)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Morpheus-233/whisper-flow.git
   cd whisper-flow
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Enable NVIDIA GPU Acceleration:**
   For NVIDIA GPUs (RTX / GTX series) using CUDA:
   ```bash
   pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
   ```

5. **Launch the application:**
   - Command line:
     ```bash
     python app.py
     ```
   - Console batch launcher: double-click `run_app.bat`
   - Silent background launcher: double-click `WhisperFlow_Silent.vbs`

---

### Option 2: Pre-Built Portable Executable

Download `WhisperFlow-windows-x64.zip` from the [GitHub Releases](https://github.com/Morpheus-233/whisper-flow/releases) page. Extract and run `WhisperFlow.exe` directly without installing Python.

---

## Usage

1. Click into any editable text box or terminal prompt.
2. Click the **Whisper Flow widget** or press **`Ctrl + Shift + Space`** to begin recording.
3. Speak naturally. The waveform displays real-time microphone levels.
4. When finished:
   - Click the checkmark button or press **`Ctrl + Shift + Space`** to transcribe and insert text.
   - Click the cancel button to discard the audio recording.

---

## Configuration and Preferences

Access preferences by right-clicking the system tray icon or selecting the settings icon:
- **Model Selection**: Choose between `tiny.en`, `base.en`, `small.en`, `medium.en`, or multilingual models.
- **Microphone Selection**: Select the desired input audio device.
- **Global Hotkey**: Configure global recording hotkeys (default: `Ctrl + Shift + Space`).
- **Show Only In Text Boxes**: Toggle between context-aware appearance or persistent dock.

User preferences are saved locally to `config.json`.

---

## Project Structure

```text
whisper-flow/
├── ui/
│   ├── floating_widget.py     # Expandable widget and dynamic animations
│   ├── settings_dialog.py     # Preferences dialog
│   └── __init__.py
├── app.py                     # Main application entry point, tray icon, and IPC
├── audio_engine.py            # Audio recording and sounddevice stream
├── config.py                  # Configuration loader and default settings
├── focus_detector.py          # Windows UI Automation text-box focus tracking
├── paster.py                  # Text pasting and clipboard injection
├── text_cleaner.py            # Post-processing and stutter removal
├── whisper_engine.py          # faster-whisper CTranslate2 transcription engine
├── WhisperFlow_Silent.vbs     # Background launcher script
├── run_app.bat                # Batch launcher script
├── create_desktop_shortcut.py # Desktop shortcut generator
├── requirements.txt           # Python package requirements
└── README.md
```

---

## License

This project is licensed under the [MIT License](LICENSE).
