# Whisper Flow

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg)](https://microsoft.com/windows)
[![Engine: faster-whisper](https://img.shields.io/badge/Engine-faster--whisper%20(CTranslate2)-orange.svg)](https://github.com/SYSTRAN/faster-whisper)
[![Cloud Engine: Groq](https://img.shields.io/badge/Cloud%20Engine-Groq%20API%20(Optional)-purple.svg)](https://groq.com)
[![Local LLM: Ollama](https://img.shields.io/badge/LLM-Ollama%20(Optional)-blueviolet.svg)](https://ollama.com)

A minimalist, high-performance voice dictation application for Windows featuring an expandable floating widget inspired by Wispr Flow, personalized voice calibration, custom vocabulary biasing, app-aware speech styles, and instant direct paste into any text box.

Whisper Flow remains hidden until you focus an editable text input in any application, expands into an interactive recording bar with live soundwave visualization, transcribes speech with low latency, applies your selected speech style, and pastes the result directly into your active window.

---

## Transcription & Privacy Modes

Whisper Flow supports two complementary transcription engines, switchable at any time from Settings or the system tray:

1. **Local Mode (Default / Offline)**:
   - Uses `faster-whisper` (CTranslate2) running 100% locally on your machine.
   - Hardware acceleration: automatically utilizes NVIDIA CUDA when available, with instant fallback to CPU (`int8`).
   - Downloads the Whisper model on first use (default: `base`). A tray notification displays progress during first-time download.
   - **Privacy**: Zero audio or text data leaves your machine. Completely offline.

2. **Groq Cloud Mode (Optional High Speed)**:
   - Uses Groq Cloud API (`whisper-large-v3-turbo` for speech recognition and `qwen/qwen3.8-27b` / Llama models for style formatting).
   - Enabled by pasting your Groq API key into Preferences.
   - **Privacy Notice**: Audio and text leave your machine ONLY when Groq Cloud mode is active and an API key is provided.

---

## Build the .exe (No Command Prompt)

You can build a standalone, windowed `WhisperFlow.exe` that runs without any command prompt window. You never have to type a single terminal command.

1. **Download the repository**:
   - Click the green **Code** button on GitHub and select **Download ZIP**.
   - Extract the downloaded ZIP file to any folder on your computer.

2. **Run the One-Click Builder**:
   - Double-click **`Build_WhisperFlow.bat`** in the extracted folder.
   - A dark-themed builder window will appear showing live progress.
   - *Python Check*: The builder automatically detects Python 3.10+. If Python is not installed, it offers to install Python 3.11 automatically via Windows Package Manager (`winget`) or opens python.org.
   - *(Optional)* Check "Include NVIDIA GPU support" if you have an NVIDIA RTX/GTX graphics card and want GPU acceleration bundled.

3. **Finished!**:
   - The compiled standalone app is placed in `WhisperFlow_App\` in the repository root.
   - A Desktop shortcut named **Whisper Flow** is created automatically.
   - Click **Launch WhisperFlow** in the builder or launch via your Desktop shortcut.

> [!NOTE]
> **Windows SmartScreen**: Because the standalone executable is built locally on your machine and is self-signed, Windows SmartScreen may show an "unknown publisher" banner on first launch. Click **More info** and then **Run anyway**.
>
> **Antivirus Software**: Antivirus or endpoint protection software may scrutinize keyboard listener and clipboard automation tools. Whisper Flow uses standard Windows UI Automation and synthetic input APIs (`pynput`, `uiautomation`, `pyautogui`) solely to detect focused text fields and insert transcribed text.

---

## Run from Source (Developers)

If you prefer to run directly from source code:

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
   ```bash
   pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
   ```

5. **(Optional) Enable Local LLM Styling with Ollama:**
   Install [Ollama](https://ollama.com) on Windows and pull your preferred model:
   ```bash
   ollama pull qwen3.5:9b-q4_K_M
   ```

6. **Launch:**
   ```bash
   python app.py
   ```

---

## Usage

1. Click into any editable text box or terminal window.
2. Click the **Whisper Flow widget** or press **`Ctrl + Shift + Space`** (default hotkey; `Ctrl + Alt + Space` also supported) to begin recording.
3. Speak naturally. The waveform capsule visualizes live microphone levels.
4. When finished:
   - Click the checkmark button or press **`Ctrl + Shift + Space`** to transcribe and insert text.
   - Click the cancel button (`X`) to discard the audio without transcribing.
5. Quick Style Switch: Right-click the floating widget or tray icon to switch between **Professional**, **Casual**, **Developer**, **Raw Cleaned**, or **Custom Persona** styles.

---

## Configuration and Preferences

Access preferences by clicking the gear icon on the widget or right-clicking the system tray icon:
- **General Tab**: Select Whisper model, audio input device, engine mode (Groq Cloud vs Local CPU), hotkey, and focus auto-show settings.
- **Voice & Styles Tab**: Choose speech styles, toggle app-aware automatic style switching, configure local Ollama, and launch the Voice Calibration Wizard.
- **Personal Dictionary Tab**: Add custom names, technical jargon, and phonetic auto-correction replacement rules.

When running as a built executable, user preferences are stored in `%APPDATA%\WhisperFlow\config.json` and `%APPDATA%\WhisperFlow\voice_profile.json` (auto-migrated from older versions on first launch), surviving rebuilds and updates. Application diagnostic logs are written to `%APPDATA%\WhisperFlow\logs\app.log` with automatic API key redaction.

---

## Project Structure

```text
whisper-flow/
├── ui/
│   ├── floating_widget.py       # Dynamic widget with recording waveform
│   ├── settings_dialog.py       # Preferences dialog (General, Voice, Dictionary)
│   ├── voice_training_dialog.py # Guided acoustic and cadence calibration wizard
│   └── __init__.py
├── app.py                       # Main application entry point, tray icon, and single-instance IPC
├── audio_engine.py              # Audio recording and sounddevice stream
├── config.py                    # Configuration management and %APPDATA% path resolution
├── focus_detector.py            # Windows UI Automation text-box focus tracking
├── paster.py                    # Text pasting and clipboard injection
├── style_engine.py              # Speech styles and Hinglish transliteration
├── text_cleaner.py              # Post-processing, verbal retractions, and stutter removal
├── voice_profile.py             # Personal vocabulary, dictionary, and acoustic settings
├── whisper_engine.py            # faster-whisper CTranslate2 & Groq Cloud engine
├── Build_WhisperFlow.bat        # One-click standalone builder entry point
├── build_gui.py                 # Tkinter progress window and build executor
├── WhisperFlow.spec             # Committed PyInstaller specification
├── create_desktop_shortcut.py   # Desktop shortcut generator
├── requirements.txt             # Python package dependencies
└── README.md
```

---

## License

This project is licensed under the [MIT License](LICENSE).
