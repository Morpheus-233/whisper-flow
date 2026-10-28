import sys
import os
import re
import threading
import time
import ctypes
from ctypes import wintypes

from config import get_app_data_dir, get_resource_path

# Dedicated file logging in %APPDATA%\WhisperFlow\logs\app.log (or local directory if not frozen)
LOG_DIR = os.path.join(get_app_data_dir(), "logs")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except Exception:
    pass
LOG_FILE = os.path.join(LOG_DIR, "app.log")

API_KEY_REGEX = re.compile(r"gsk_[a-zA-Z0-9_-]{15,}")

def sanitize_log(msg: str) -> str:
    """Sanitizes sensitive Groq API keys from all written logs and exception dumps."""
    if not isinstance(msg, str):
        msg = str(msg)
    return API_KEY_REGEX.sub("gsk_***", msg)

def log_debug(msg):
    try:
        clean_msg = sanitize_log(msg)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {clean_msg}\n")
    except Exception:
        pass

class SafeStream:
    def write(self, s):
        if s and s.strip():
            log_debug(s.strip())
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = SafeStream()
if sys.stderr is None:
    sys.stderr = SafeStream()

def exception_hook(exctype, value, tb):
    import traceback
    try:
        formatted = "".join(traceback.format_exception(exctype, value, tb))
        clean_formatted = sanitize_log(formatted)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n--- UNCAUGHT EXCEPTION: {exctype.__name__} ---\n{clean_formatted}\n")
    except Exception:
        pass
    if sys.__excepthook__:
        try:
            sys.__excepthook__(exctype, value, tb)
        except Exception:
            pass

sys.excepthook = exception_hook

if hasattr(threading, "excepthook"):
    def thread_exception_hook(args):
        import traceback
        try:
            formatted = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
            clean_formatted = sanitize_log(formatted)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n--- UNCAUGHT THREAD EXCEPTION [{args.thread.name if args.thread else 'unknown'}] ---\n{clean_formatted}\n")
        except Exception:
            pass
    threading.excepthook = thread_exception_hook

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

ERROR_ALREADY_EXISTS = 183
SINGLE_INSTANCE_MUTEX_NAME = "Local\\WhisperFlow_SingleInstance_Mutex_v3"
SINGLE_INSTANCE_IPC_NAME = "WhisperFlow_IPC_SingleInstance_v3"
WM_SHOW_WHISPER_FLOW = user32.RegisterWindowMessageW("WHISPER_FLOW_SHOW_WIDGET_V3")

_primary_mutex_handle = None

def _run_fast_instance_check():
    global _primary_mutex_handle
    mutex_handle = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX_NAME)
    mutex_err = ctypes.GetLastError()

    if mutex_err == ERROR_ALREADY_EXISTS:
        log_debug("Existing instance detected via fast-path named mutex. Broadcasting SHOW signal and exiting (<100ms).")
        # 1. Grant permission to existing instance to take foreground
        try:
            user32.AllowSetForegroundWindow(0xFFFFFFFF)
        except Exception:
            pass

        # 2. Channel A: Native Win32 broadcast message (always delivered to top-level windows)
        try:
            user32.PostMessageW(0xFFFF, WM_SHOW_WHISPER_FLOW, 0, 0)
        except Exception:
            pass

        # 3. Channel B: Fast named pipe signal (pure Win32, zero Qt overhead)
        try:
            pipe_name = r"\\.\pipe\WhisperFlow_IPC_SingleInstance_v3"
            h_pipe = kernel32.CreateFileW(
                pipe_name,
                0x40000000,  # GENERIC_WRITE
                0,
                None,
                3,           # OPEN_EXISTING
                0,
                None
            )
            if h_pipe != -1 and h_pipe != 0:
                written = wintypes.DWORD(0)
                msg = b"SHOW\n"
                kernel32.WriteFile(h_pipe, msg, len(msg), ctypes.byref(written), None)
                kernel32.CloseHandle(h_pipe)
        except Exception as e:
            log_debug(f"Fast-path pipe write notice: {e}")

        if mutex_handle:
            try:
                kernel32.CloseHandle(mutex_handle)
            except Exception:
                pass

        sys.exit(0)

    _primary_mutex_handle = mutex_handle

# Hoist fast-path named mutex check before heavy module imports (PySide6, faster-whisper, torch, focus_detector)
if __name__ == "__main__":
    _run_fast_instance_check()

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtCore import Qt, QObject, Signal, Slot, QTimer, QPoint
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from config import load_config, save_config
from audio_engine import AudioEngine
from whisper_engine import WhisperEngine
from paster import Paster
from text_cleaner import clean_speech_text
from focus_detector import FocusDetector
from ui.floating_widget import (
    FloatingWidget, STATE_IDLE, STATE_RECORDING, 
    STATE_TRANSCRIBING, STATE_PASTED
)
from ui.settings_dialog import SettingsDialog
from ui.voice_training_dialog import VoiceTrainingDialog
from voice_profile import VoiceProfileManager
from style_engine import StyleEngine

class AppSignals(QObject):
    toggle_recording = Signal()
    transcription_done = Signal(str)
    paste_completed = Signal()
    mouse_clicked = Signal(int, int)
    focus_changed = Signal()
    status_message = Signal(str)

class WhisperFlowApp:
    def __init__(self):
        self.config = load_config()
        self.signals = AppSignals()

        # Engine instances
        self.audio_engine = AudioEngine(
            sample_rate=16000, 
            device_index=self.config.get("input_device_index")
        )
        self.whisper_engine = WhisperEngine.get_instance(
            model_name=self.config.get("model_name", "base.en")
        )
        self.whisper_engine.on_status_callback = lambda msg: self.signals.status_message.emit(msg)
        self.paster = Paster()
        self.voice_profile = VoiceProfileManager.get_instance()
        self.style_engine = StyleEngine.get_instance()
        self.style_engine.prewarm()

        # Continuous foreground window handle tracker for targeting pastes
        self.last_foreground_hwnd = None

        # Manual show grace timer (2.5 seconds): brief startup visual confirmation
        self.manual_show_until = time.time() + 2.5

        # GUI Widget (starts visible for launch confirmation, then gracefully docks/auto-hides)
        self.widget = FloatingWidget(self.config, self.audio_engine)
        self.widget.show_requested_from_external.connect(self.show_widget_requested)

        # Initialize live status badges on floating widget & whisper engine
        init_engine = self.config.get("engine_mode", "groq")
        init_lang = self.config.get("language_mode", "hinglish")
        init_style = self.voice_profile.get_active_style()
        self.whisper_engine.engine_mode = init_engine
        self.widget.update_status_badges(init_engine, init_lang, init_style)

        # Fast Debounced Visibility Controller (25ms debounce for snappy response)
        self.visibility_debounce_timer = QTimer(self.widget)
        self.visibility_debounce_timer.setSingleShot(True)
        self.visibility_debounce_timer.timeout.connect(self._evaluate_visibility)

        # Fast periodic fallback check (every 50ms) to ensure seamless tracking across apps
        self.periodic_focus_timer = QTimer(self.widget)
        self.periodic_focus_timer.timeout.connect(self._on_periodic_tick)
        self.periodic_focus_timer.start(50)

        self._setup_connections()
        self.manual_show_until = time.time() + 15.0
        self.widget.show()
        self.widget.raise_()

        # Text Box Focus Detector with UIA event handling
        self.focus_detector = FocusDetector(
            widget_hwnd_getter=lambda: int(self.widget.winId()) if self.widget else 0,
            on_focus_changed=self._on_uia_focus_changed
        )
        self.auto_show_on_textbox = self.config.get("auto_show_on_textbox", True)

        # System Tray Icon & Context Menu
        self._setup_tray_icon()

        # Global Mouse Click Listener to immediately react to user clicks in any app
        self.mouse_listener = None
        self._start_mouse_listener()

        # Global Hotkey Listener (Ctrl+Shift+Space & Ctrl+Alt+Space)
        self.keyboard_listener = None
        self._start_hotkey_listener()

        # Pre-warm Whisper Model in background so transcription is instant
        threading.Thread(target=self._prewarm_model, daemon=True).start()

        # Initial visibility evaluation after window subsystem stabilizes (30ms)
        self.visibility_debounce_timer.start(30)

    def _setup_connections(self):
        self.widget.toggle_recording_requested.connect(self.toggle_recording)
        self.widget.cancel_recording_requested.connect(self.cancel_recording)
        self.widget.open_settings_requested.connect(self.open_settings)
        self.widget.open_studio_requested.connect(self.launch_web_voice_studio)
        self.widget.model_changed.connect(self.change_model)
        self.widget.engine_changed.connect(self._on_engine_changed)
        self.widget.language_changed.connect(self._on_language_changed)
        self.widget.exit_requested.connect(self.exit_app)

        self.signals.toggle_recording.connect(self.toggle_recording)
        self.signals.transcription_done.connect(self._handle_transcription_done)
        self.signals.paste_completed.connect(self._on_paste_completed)
        self.signals.mouse_clicked.connect(self._on_mouse_clicked)
        self.signals.focus_changed.connect(self._on_focus_changed)
        self.signals.status_message.connect(self._show_tray_message)

    @Slot(str)
    def _show_tray_message(self, msg: str):
        log_debug(f"[Tray Notification] {msg}")
        if hasattr(self, 'tray_icon') and self.tray_icon and QSystemTrayIcon.isSystemTrayAvailable():
            try:
                self.tray_icon.showMessage("Whisper Flow", msg, QSystemTrayIcon.MessageIcon.Information, 4500)
            except Exception:
                pass

    @Slot(str)
    def _on_engine_changed(self, mode: str):
        self.config["engine_mode"] = mode
        save_config(self.config)
        if self.whisper_engine:
            self.whisper_engine.engine_mode = mode
        cur_lang = self.config.get("language_mode", "hinglish")
        cur_style = self.voice_profile.get_active_style()
        self.widget.update_status_badges(mode, cur_lang, cur_style)
        self._sync_tray_engine_and_lang()

    @Slot(str)
    def _on_language_changed(self, lang: str):
        self.config["language_mode"] = lang
        save_config(self.config)
        cur_engine = self.config.get("engine_mode", "groq")
        cur_style = self.voice_profile.get_active_style()
        self.widget.update_status_badges(cur_engine, lang, cur_style)
        self._sync_tray_engine_and_lang()

    @Slot(str)
    def _on_style_changed(self, style: str):
        self.voice_profile.set_active_style(style)
        cur_engine = self.config.get("engine_mode", "groq")
        cur_lang = self.config.get("language_mode", "hinglish")
        self.widget.update_status_badges(cur_engine, cur_lang, style)
        if hasattr(self, 'style_action_group'):
            for k, a in self.style_action_group.items():
                a.setChecked(k == style)

    def _on_uia_focus_changed(self):
        """Called from UIA background COM worker thread when focus changes."""
        self.signals.focus_changed.emit()

    @Slot()
    def _on_focus_changed(self):
        """Instant visibility evaluation upon focus change event."""
        self.manual_show_until = 0
        if hasattr(self, 'visibility_debounce_timer'):
            self.visibility_debounce_timer.start(20)

    @Slot(int, int)
    def _on_mouse_clicked(self, x, y):
        """Instant visibility evaluation upon global mouse click."""
        self.manual_show_until = 0
        if hasattr(self, 'visibility_debounce_timer'):
            self.visibility_debounce_timer.start(20)

    def _on_periodic_tick(self):
        """Periodic safety tick to guarantee state consistency even if events drop."""
        self._evaluate_visibility()

    def _evaluate_visibility(self):
        """
        THE SINGLE VISIBILITY CONTROLLER:
        - Shows the widget ONLY while an editable text input has keyboard focus.
        - Keeps widget visible while dictation is actively recording / transcribing / pasting.
        - Hides the widget at all other times (canvas, playlists, buttons, desktop, password, etc.).
        - Keeps the widget at its user-specified fixed position regardless of monitor or text box.
        """
        try:
            if getattr(self, 'is_dialog_open', False):
                return

            fg = user32.GetForegroundWindow()
            widget_hwnd = int(self.widget.winId()) if self.widget else 0
            if fg and fg != widget_hwnd and user32.IsWindow(fg):
                self.last_foreground_hwnd = fg

            # 1. While actively recording, transcribing, or displaying paste confirmation,
            # maintain visibility until recording stops, even if focus shifts briefly.
            if self.widget.current_state != STATE_IDLE:
                if not self.widget.isVisible():
                    self.widget.show()
                return

            # 2. While manual show grace period is active (initial app launch, desktop icon click, tray click)
            if hasattr(self, 'manual_show_until') and time.time() < self.manual_show_until:
                if not self.widget.isVisible():
                    self.widget.show()
                return

            # 3. If user explicitly turned off "Show Only In Text Boxes", widget stays visible
            if not self.auto_show_on_textbox:
                if not self.widget.isVisible():
                    self.widget.show()
                return

            # 4. Query the element-level focus detector
            is_text_field, rect = self.focus_detector.get_focused_text_input()

            if is_text_field:
                # An editable text field has active keyboard focus!
                if not self.widget.isVisible():
                    self.widget.show()
            else:
                # Focus is not on an editable text input (button, canvas, playlist, desktop, etc.)
                if self.widget.isVisible():
                    self.widget.hide()
        except Exception as e:
            print(f"[Visibility Controller] Error: {e}")

    def _on_paste_completed(self):
        self.widget.set_state(STATE_PASTED)
        # After the 280ms paste confirmation returns to idle, re-evaluate focus
        QTimer.singleShot(350, self._evaluate_visibility)

    def _start_mouse_listener(self):
        """Global mouse listener to immediately detect text box clicks anywhere in Windows."""
        try:
            from pynput import mouse

            def on_click(x, y, button, pressed):
                # If click was on our widget, ignore so widget buttons aren't disturbed
                if not pressed:
                    return
                if self.widget and self.widget.isVisible():
                    geom = self.widget.geometry()
                    if geom.contains(int(x), int(y)):
                        return
                self.signals.mouse_clicked.emit(int(x), int(y))

            self.mouse_listener = mouse.Listener(on_click=on_click)
            self.mouse_listener.daemon = True
            self.mouse_listener.start()
        except Exception as e:
            print(f"[App] Mouse listener notice: {e}")

    def _create_tray_icon_pixmap(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(102, 50, 107))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 28, 28)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(12, 12, 8, 8)
        painter.end()
        return pixmap

    def _setup_tray_icon(self):
        icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
        else:
            app_icon = QIcon(self._create_tray_icon_pixmap())
        self.tray_icon = QSystemTrayIcon(app_icon, self.widget)
        self.tray_icon.setToolTip("Whisper Flow (Ctrl+Shift+Space)")

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #1a1622;
                color: #f8fafc;
                border: 1px solid #334155;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #66326b;
            }
        """)

        show_action = tray_menu.addAction("Show Widget")
        show_action.triggered.connect(self.manual_show_widget)

        record_action = tray_menu.addAction("Record / Stop (Ctrl+Shift+Space)")
        record_action.triggered.connect(self.toggle_recording)

        tray_menu.addSeparator()

        self.auto_show_action = tray_menu.addAction("Show Only In Text Boxes")
        self.auto_show_action.setCheckable(True)
        self.auto_show_action.setChecked(self.auto_show_on_textbox)

        def _on_toggle_auto_show():
            self.auto_show_on_textbox = self.auto_show_action.isChecked()
            self.config["auto_show_on_textbox"] = self.auto_show_on_textbox
            save_config(self.config)
            self._evaluate_visibility()

        self.auto_show_action.triggered.connect(_on_toggle_auto_show)

        # Direct Engine Toggle Submenu (Groq Cloud / Local CPU)
        engine_menu = tray_menu.addMenu("Engine Mode")
        self.engine_action_group = {}
        cur_engine = self.config.get("engine_mode", "groq")
        for e_label, e_key in [("Groq Cloud (0% CPU)", "groq"), ("Local CPU (int8 Offline)", "local")]:
            act = engine_menu.addAction(e_label)
            act.setCheckable(True)
            act.setChecked(e_key == cur_engine)
            def _make_e_h(k=e_key):
                return lambda: self._on_engine_changed(k)
            act.triggered.connect(_make_e_h(e_key))
            self.engine_action_group[e_key] = act

        # Direct Language Toggle Submenu (Hinglish / English)
        lang_menu = tray_menu.addMenu("Language Mode")
        self.lang_action_group = {}
        cur_lang = self.config.get("language_mode", "hinglish")
        for l_label, l_key in [("Hinglish (Hindi + English)", "hinglish"), ("English Only", "en")]:
            act = lang_menu.addAction(l_label)
            act.setCheckable(True)
            act.setChecked(l_key == cur_lang)
            def _make_l_h(k=l_key):
                return lambda: self._on_language_changed(k)
            act.triggered.connect(_make_l_h(l_key))
            self.lang_action_group[l_key] = act

        # Speech Style Submenu
        style_menu = tray_menu.addMenu("Speech Style")
        self.style_action_group = {}
        styles = [
            ("Professional / Executive", "professional"),
            ("Casual Chat", "casual"),
            ("Developer / Code", "code"),
            ("Raw Cleaned", "raw"),
            ("Custom Persona", "custom")
        ]
        cur_style = self.voice_profile.get_active_style()
        for title, key in styles:
            act = style_menu.addAction(title)
            act.setCheckable(True)
            act.setChecked(key == cur_style)
            def _make_handler(s_key=key):
                def _handler():
                    self.voice_profile.set_active_style(s_key)
                    for k, a in self.style_action_group.items():
                        a.setChecked(k == s_key)
                return _handler
            act.triggered.connect(_make_handler(key))
            self.style_action_group[key] = act

        wizard_action = tray_menu.addAction("Voice Calibration Wizard...")
        wizard_action.triggered.connect(lambda: QTimer.singleShot(0, self._launch_calibration_wizard))

        studio_action = tray_menu.addAction("Web Voice Studio (100 Sentences)...")
        studio_action.triggered.connect(lambda: QTimer.singleShot(0, self.launch_web_voice_studio))

        tray_menu.addSeparator()

        settings_action = tray_menu.addAction("Preferences...")
        settings_action.triggered.connect(lambda: QTimer.singleShot(0, self.open_settings))

        quit_action = tray_menu.addAction("Exit Whisper Flow")
        quit_action.triggered.connect(lambda: QTimer.singleShot(0, self.exit_app))

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _sync_tray_engine_and_lang(self):
        cur_engine = self.config.get("engine_mode", "groq")
        cur_lang = self.config.get("language_mode", "hinglish")
        if hasattr(self, 'engine_action_group'):
            for k, a in self.engine_action_group.items():
                a.setChecked(k == cur_engine)
        if hasattr(self, 'lang_action_group'):
            for k, a in self.lang_action_group.items():
                a.setChecked(k == cur_lang)

    def manual_show_widget(self):
        """Explicitly shows and raises the widget upon manual user request."""
        self.manual_show_until = time.time() + 30.0
        self.widget.show()
        self.widget.raise_()
        self.widget.activateWindow()
        self._evaluate_visibility()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if not self.widget.isVisible():
                self.manual_show_widget()
            else:
                self.widget.hide()

    def _start_hotkey_listener(self):
        """Global background keyboard hotkey listener for Ctrl+Shift+Space and Ctrl+Alt+Space."""
        try:
            from pynput import keyboard
            current_keys = set()
            last_trigger_time = 0

            def on_press(key):
                nonlocal last_trigger_time
                current_keys.add(key)

                is_ctrl = any(k in current_keys for k in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.ctrl])
                is_shift = any(k in current_keys for k in [keyboard.Key.shift_l, keyboard.Key.shift_r, keyboard.Key.shift])
                is_alt = any(k in current_keys for k in [keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr, keyboard.Key.alt])
                is_space = (key == keyboard.Key.space)

                if is_space and is_ctrl and (is_shift or is_alt):
                    now = time.time()
                    if now - last_trigger_time > 0.4:
                        last_trigger_time = now
                        self.signals.toggle_recording.emit()

            def on_release(key):
                current_keys.discard(key)

            self.keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self.keyboard_listener.daemon = True
            self.keyboard_listener.start()
        except Exception as e:
            print(f"[App] Global hotkey listener notice: {e}")

    def _prewarm_model(self):
        print("[App] Pre-warming Whisper model...")
        self.whisper_engine.load_model()
        print("[App] Whisper model is warm and ready!")

    def toggle_recording(self):
        if self.audio_engine.is_recording:
            self.stop_recording()
        else:
            self.manual_show_until = time.time() + 30.0
            if not self.widget.isVisible():
                self.widget.show()
                self.widget.raise_()
            self.start_recording()

    def start_recording(self):
        if self.audio_engine.is_recording:
            return

        self.audio_engine.start_recording()
        self.widget.set_state(STATE_RECORDING)

    def cancel_recording(self):
        """Cancels recording without transcribing or pasting."""
        if self.audio_engine.is_recording:
            print("[App] Recording cancelled by user via X button.")
            self.audio_engine.stop_recording()
        self.widget.set_state(STATE_IDLE)
        self.visibility_debounce_timer.start(120)

    def stop_recording(self):
        if not self.audio_engine.is_recording:
            return

        audio_data = self.audio_engine.stop_recording()

        if len(audio_data) < 16000 * 0.3:
            self.widget.set_state(STATE_IDLE)
            self.visibility_debounce_timer.start(120)
            return

        self.widget.set_state(STATE_TRANSCRIBING)

        def transcribe_worker():
            try:
                # 1. Custom Vocabulary Biasing for Whisper Token Decoder
                initial_prompt = self.voice_profile.get_initial_prompt()

                raw_text = self.whisper_engine.transcribe(
                    audio_data, 
                    initial_prompt=initial_prompt,
                    remove_trailing_stop=False
                )

                # 2. Phonetic / Custom Dictionary Replacements
                replaced_text = self.voice_profile.apply_replacements(raw_text)

                # 3. Determine active target application for App-Aware Styling
                win_title = ""
                win_class = ""
                if self.last_foreground_hwnd and user32.IsWindow(self.last_foreground_hwnd):
                    buf = ctypes.create_unicode_buffer(512)
                    user32.GetWindowTextW(self.last_foreground_hwnd, buf, 512)
                    win_title = buf.value
                    user32.GetClassNameW(self.last_foreground_hwnd, buf, 512)
                    win_class = buf.value

                effective_style = self.voice_profile.get_effective_style(win_title, win_class)

                # 4. Ollama / Stylist Transformation
                styled_text = self.style_engine.transform_text(
                    replaced_text,
                    target_style=effective_style
                )

                self.signals.transcription_done.emit(styled_text)
            except Exception as e:
                print(f"Error during transcription: {e}")
                self.signals.transcription_done.emit("")

        threading.Thread(target=transcribe_worker, daemon=True).start()

    @Slot(str)
    def _handle_transcription_done(self, text):
        if not text or not text.strip():
            self.widget.set_state(STATE_IDLE)
            self.visibility_debounce_timer.start(120)
            return

        print(f"[Whisper Flow] Cleaned Transcription: \"{text}\"")

        def on_pasted():
            self.signals.paste_completed.emit()

        widget_hwnd = int(self.widget.winId()) if self.widget else 0

        # Perform instant paste into target window
        self.paster.instant_paste(
            text=text,
            target_hwnd=self.last_foreground_hwnd,
            widget_hwnd=widget_hwnd,
            on_pasted_callback=on_pasted
        )

    def change_model(self, model_name):
        self.config["model_name"] = model_name
        save_config(self.config)
        self.whisper_engine = WhisperEngine.get_instance(model_name)
        threading.Thread(target=self._prewarm_model, daemon=True).start()

    def open_settings(self, bring_to_front=True):
        if getattr(self, 'is_dialog_open', False):
            if hasattr(self, 'active_dialog') and self.active_dialog:
                try:
                    user32.ReleaseCapture()
                    if self.active_dialog.isMinimized():
                        self.active_dialog.showNormal()
                    self.active_dialog.raise_()
                    self.active_dialog.activateWindow()
                    user32.SetForegroundWindow(int(self.active_dialog.winId()))
                except Exception:
                    pass
            return

        def _do_open():
            if getattr(self, 'is_dialog_open', False):
                return
            self.is_dialog_open = True
            try:
                try:
                    user32.ReleaseCapture()
                except Exception:
                    pass

                dlg = SettingsDialog(self.config, self.audio_engine, self.whisper_engine, parent=None)
                self.active_dialog = dlg
                dlg.engine_changed.connect(self._on_engine_changed)
                dlg.language_changed.connect(self._on_language_changed)
                dlg.style_changed.connect(self._on_style_changed)

                if bring_to_front:
                    try:
                        primary_screen = QApplication.primaryScreen()
                        if primary_screen:
                            screen_geo = primary_screen.availableGeometry()
                            x = screen_geo.x() + (screen_geo.width() - dlg.width()) // 2
                            y = screen_geo.y() + (screen_geo.height() - dlg.height()) // 2
                            dlg.move(x, y)
                    except Exception:
                        pass

                def _raise_dlg():
                    try:
                        dlg.raise_()
                        dlg.activateWindow()
                        user32.SetForegroundWindow(int(dlg.winId()))
                    except Exception:
                        pass
                QTimer.singleShot(0, _raise_dlg)

                if dlg.exec():
                    save_config(self.config)
                    self.audio_engine.device_index = self.config.get("input_device_index")
                    self.auto_show_on_textbox = self.config.get("auto_show_on_textbox", True)
                    if hasattr(self, 'auto_show_action'):
                        self.auto_show_action.setChecked(self.auto_show_on_textbox)
                    self.visibility_debounce_timer.start(50)
                    if self.whisper_engine:
                        self.whisper_engine.engine_mode = self.config.get("engine_mode", "groq")
                        if self.whisper_engine.model_name != self.config.get("model_name"):
                            self.whisper_engine = WhisperEngine.get_instance(self.config.get("model_name"))
                            threading.Thread(target=self._prewarm_model, daemon=True).start()
                    self.widget.update_status_badges(
                        self.config.get("engine_mode", "groq"),
                        self.config.get("language_mode", "hinglish"),
                        self.voice_profile.get_active_style()
                    )
                    self._sync_tray_engine_and_lang()
            finally:
                self.active_dialog = None
                self.is_dialog_open = False

        QTimer.singleShot(0, _do_open)

    def _launch_calibration_wizard(self):
        if getattr(self, 'is_dialog_open', False):
            if hasattr(self, 'active_dialog') and self.active_dialog:
                try:
                    user32.ReleaseCapture()
                    if self.active_dialog.isMinimized():
                        self.active_dialog.showNormal()
                    self.active_dialog.raise_()
                    self.active_dialog.activateWindow()
                    user32.SetForegroundWindow(int(self.active_dialog.winId()))
                except Exception:
                    pass
            return

        def _do_wiz():
            if getattr(self, 'is_dialog_open', False):
                return
            self.is_dialog_open = True
            try:
                try:
                    user32.ReleaseCapture()
                except Exception:
                    pass

                wiz = VoiceTrainingDialog(self.audio_engine, self.whisper_engine, parent=None)
                self.active_dialog = wiz

                try:
                    primary_screen = QApplication.primaryScreen()
                    if primary_screen:
                        screen_geo = primary_screen.availableGeometry()
                        x = screen_geo.x() + (screen_geo.width() - wiz.width()) // 2
                        y = screen_geo.y() + (screen_geo.height() - wiz.height()) // 2
                        wiz.move(x, y)
                except Exception:
                    pass

                def _raise_wiz():
                    try:
                        wiz.raise_()
                        wiz.activateWindow()
                        user32.SetForegroundWindow(int(wiz.winId()))
                    except Exception:
                        pass
                QTimer.singleShot(0, _raise_wiz)

                wiz.exec()
            finally:
                self.active_dialog = None
                self.is_dialog_open = False

        QTimer.singleShot(0, _do_wiz)

    def launch_web_voice_studio(self):
        """Launches the lightweight Web Voice Studio server if not active, and opens browser."""
        def _do_studio():
            import socket
            import subprocess
            import webbrowser

            is_running = False
            try:
                with socket.create_connection(("127.0.0.1", 8000), timeout=0.2):
                    is_running = True
            except Exception:
                is_running = False

            if not is_running:
                if getattr(sys, "frozen", False):
                    try:
                        import studio_server
                        threading.Thread(target=studio_server.run_server, kwargs={"port": 8000}, daemon=True).start()
                        time.sleep(0.4)
                    except Exception as e:
                        log_debug(f"Error launching frozen studio server: {e}")
                else:
                    server_script = get_resource_path("studio_server.py")
                    if os.path.exists(server_script):
                        python_exe = sys.executable
                        subprocess.Popen([python_exe, server_script], cwd=os.path.dirname(server_script))
                        time.sleep(0.4)

            webbrowser.open("http://127.0.0.1:8000")

        QTimer.singleShot(0, _do_studio)

    def show_widget_requested(self):
        """
        Invoked when another instance launch is attempted (e.g. user double-clicked Desktop icon).
        Explicitly shows the widget and opens Preferences so the user gets immediate visual confirmation.
        """
        self.manual_show_until = time.time() + 60.0
        if self.widget.isMinimized():
            self.widget.showNormal()
        self.widget.show()
        self.widget.raise_()
        try:
            hwnd = int(self.widget.winId())
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        self.widget.activateWindow()
        self._evaluate_visibility()
        self.open_settings(bring_to_front=True)

    def exit_app(self):
        log_debug("exit_app: shutting down application")
        try:
            # 1. Immediately hide UI from screen (both Qt and Win32 SW_HIDE)
            if hasattr(self, 'widget') and self.widget:
                self.widget.hide()
                try:
                    hwnd = int(self.widget.winId()) if self.widget else 0
                    if hwnd:
                        user32.ShowWindow(hwnd, 0)  # SW_HIDE
                except Exception:
                    pass
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.hide()
        except Exception as e:
            log_debug(f"exit_app hide error: {e}")

        try:
            # 2. Stop audio recording if in progress
            if hasattr(self, 'audio_engine') and self.audio_engine and self.audio_engine.is_recording:
                self.audio_engine.stop_recording()
        except Exception as e:
            log_debug(f"exit_app audio stop error: {e}")

        try:
            # 3. Save configuration
            save_config(self.config)
        except Exception as e:
            log_debug(f"exit_app save_config error: {e}")

        try:
            # 4. Release single-instance mutex and IPC server
            if hasattr(self, 'mutex_handle') and self.mutex_handle:
                kernel32.CloseHandle(self.mutex_handle)
                self.mutex_handle = None
            if hasattr(self, 'ipc_server') and self.ipc_server:
                self.ipc_server.close()
                QLocalServer.removeServer(SINGLE_INSTANCE_IPC_NAME)
        except Exception as e:
            log_debug(f"exit_app mutex/ipc error: {e}")

        log_debug("exit_app: clean exit complete, invoking TerminateProcess/os._exit(0)")
        try:
            kernel32.TerminateProcess(kernel32.GetCurrentProcess(), 0)
        except Exception:
            pass
        os._exit(0)

def main(mutex_handle=None):
    log_debug("=== main() started ===")
    try:
        if mutex_handle is None:
            mutex_handle = _primary_mutex_handle
            if mutex_handle is None:
                _run_fast_instance_check()
                mutex_handle = _primary_mutex_handle

        # Primary instance: initialize Qt application
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))

        # Clean up any leftover dead pipe/socket from a prior crash or reboot
        QLocalServer.removeServer(SINGLE_INSTANCE_IPC_NAME)

        log_debug("Initializing WhisperFlowApp...")
        flow = WhisperFlowApp()
        flow.mutex_handle = mutex_handle
        log_debug("WhisperFlowApp initialized successfully.")

        # 2. Start IPC Server to listen for future launch attempts
        ipc_server = QLocalServer()
        if ipc_server.listen(SINGLE_INSTANCE_IPC_NAME):
            log_debug(f"IPC server listening on {SINGLE_INSTANCE_IPC_NAME}")
            def on_new_connection():
                client = ipc_server.nextPendingConnection()
                if not client:
                    return
                def on_read():
                    try:
                        data = bytes(client.readAll()).decode("utf-8", errors="ignore")
                        log_debug(f"IPC server received command: {data.strip()}")
                        if "SHOW" in data:
                            flow.show_widget_requested()
                        elif "EXIT" in data:
                            flow.exit_app()
                    except Exception as e:
                        log_debug(f"IPC Server error handling command: {e}")
                client.readyRead.connect(on_read)
            ipc_server.newConnection.connect(on_new_connection)
            flow.ipc_server = ipc_server
        else:
            log_debug(f"IPC Server warning: Could not listen on {SINGLE_INSTANCE_IPC_NAME}: {ipc_server.errorString()}")

        log_debug("Entering Qt application event loop (app.exec)...")
        exit_code = app.exec()
        log_debug(f"app.exec() exited with code: {exit_code}")
        try:
            kernel32.TerminateProcess(kernel32.GetCurrentProcess(), exit_code)
        except Exception:
            pass
        os._exit(exit_code)
    except SystemExit as se:
        log_debug(f"SystemExit encountered: {se.code}")
        raise
    except BaseException as be:
        import traceback
        log_debug(f"FATAL EXCEPTION in main(): {type(be).__name__}: {be}")
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass
        raise

if __name__ == "__main__":
    main(_primary_mutex_handle)
