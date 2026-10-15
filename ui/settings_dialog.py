import os
import time
import threading
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QGroupBox, QTabWidget, QWidget, QCheckBox,
    QLineEdit, QListWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from voice_profile import VoiceProfileManager
from style_engine import StyleEngine

class SettingsDialog(QDialog):
    def __init__(self, config, audio_engine, whisper_engine=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.audio_engine = audio_engine
        self.whisper_engine = whisper_engine
        self.profile_mgr = VoiceProfileManager.get_instance()
        self.profile = self.profile_mgr.profile

        self.setWindowTitle("Whisper Flow - Preferences")
        self.setFixedSize(520, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 13px;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                background-color: #111827;
                padding: 12px;
            }
            QTabBar::tab {
                background: #1e293b;
                color: #94a3b8;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 18px;
                margin-right: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: #3b82f6;
                color: white;
            }
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 12px;
                font-weight: bold;
                color: #93c5fd;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #3b82f6;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton#secondaryBtn {
                background-color: #334155;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #475569;
            }
            QPushButton#actionBtn {
                background-color: #4f46e5;
            }
            QPushButton#actionBtn:hover {
                background-color: #4338ca;
            }
            QLineEdit, QTextEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QListWidget, QTableWidget {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QTableWidget QHeaderView::section {
                background-color: #0f172a;
                color: #93c5fd;
                padding: 4px;
                border: 1px solid #334155;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Title
        title_label = QLabel("Whisper Flow Preferences")
        title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #60a5fa;")
        layout.addWidget(title_label)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_general = self._create_general_tab()
        self.tab_voice = self._create_voice_tab()
        self.tab_dictionary = self._create_dictionary_tab()

        self.tabs.addTab(self.tab_general, "General")
        self.tabs.addTab(self.tab_voice, "Voice & Styles")
        self.tabs.addTab(self.tab_dictionary, "Personal Dictionary")
        layout.addWidget(self.tabs)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Preferences")
        save_btn.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _create_general_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setSpacing(14)

        # Whisper Model
        model_group = QGroupBox("Whisper Model (Speech-to-Text)")
        m_layout = QVBoxLayout(model_group)
        self.model_combo = QComboBox()
        models = [
            ("small - Hindi + Indian Accent (~150ms)", "small"),
            ("base - Multilingual / Hindi (~60ms)", "base"),
            ("base.en - English Only Default (~50ms)", "base.en"),
            ("small.en - Precise English Only (~150ms)", "small.en"),
            ("tiny.en - Ultra-fast English (~40ms)", "tiny.en"),
        ]
        current_model = self.config.get("model_name", "base.en")
        selected_idx = 0
        for idx, (label, val) in enumerate(models):
            self.model_combo.addItem(label, val)
            if val == current_model:
                selected_idx = idx
        self.model_combo.setCurrentIndex(selected_idx)
        m_layout.addWidget(self.model_combo)
        l.addWidget(model_group)

        # Microphone Input
        audio_group = QGroupBox("Microphone Input")
        a_layout = QVBoxLayout(audio_group)
        self.device_combo = QComboBox()
        self.device_combo.addItem("Default System Microphone", None)
        try:
            devices = self.audio_engine.get_input_devices()
            cur_dev = self.config.get("input_device_index")
            dev_idx = 0
            for i, (d_id, d_name) in enumerate(devices):
                self.device_combo.addItem(f"{d_name} (ID: {d_id})", d_id)
                if d_id == cur_dev:
                    dev_idx = i + 1
            self.device_combo.setCurrentIndex(dev_idx)
        except Exception:
            pass
        a_layout.addWidget(self.device_combo)
        l.addWidget(audio_group)

        # Behavior
        behavior_group = QGroupBox("Focus Behavior")
        b_layout = QVBoxLayout(behavior_group)
        self.auto_show_check = QCheckBox("Show widget only when clicking into a text box")
        self.auto_show_check.setStyleSheet("color: #f8fafc; font-size: 13px;")
        self.auto_show_check.setChecked(self.config.get("auto_show_on_textbox", True))
        b_layout.addWidget(self.auto_show_check)
        l.addWidget(behavior_group)

        # Cloud Speech Fallback (Groq API)
        groq_group = QGroupBox("Cloud Speech Fallback (Optional Groq Whisper)")
        g_layout = QVBoxLayout(groq_group)
        self.groq_key_input = QLineEdit()
        self.groq_key_input.setPlaceholderText("Enter Groq API Key (gsk_...) for 0% CPU cloud Whisper")
        self.groq_key_input.setText(self.config.get("groq_api_key", ""))
        self.groq_key_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        g_layout.addWidget(self.groq_key_input)
        l.addWidget(groq_group)

        # Info
        info_label = QLabel("Global Shortcut: Ctrl + Shift + Space\nAutomatically types directly into your active text box.")
        info_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-style: italic;")
        l.addWidget(info_label)
        l.addStretch()

        return tab

    def _create_voice_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setSpacing(12)

        # Web Voice Studio (100 Sentences) Button
        studio_row = QHBoxLayout()
        studio_lbl = QLabel("100-Sentence Studio (Calibrate English & Hindi / Hinglish):")
        studio_lbl.setStyleSheet("color: #93c5fd; font-weight: bold;")
        studio_row.addWidget(studio_lbl)
        
        self.studio_btn = QPushButton("Open Web Studio")
        self.studio_btn.setObjectName("actionBtn")
        self.studio_btn.clicked.connect(self._launch_web_studio)
        studio_row.addWidget(self.studio_btn)
        l.addLayout(studio_row)

        # Voice Training Wizard Button
        train_row = QHBoxLayout()
        train_lbl = QLabel("Acoustic Calibration (Microphone gain & room noise floor):")
        train_lbl.setStyleSheet("color: #93c5fd; font-weight: bold;")
        train_row.addWidget(train_lbl)
        
        self.wizard_btn = QPushButton("Voice Calibration Wizard")
        self.wizard_btn.setObjectName("secondaryBtn")
        self.wizard_btn.clicked.connect(self._launch_wizard)
        train_row.addWidget(self.wizard_btn)
        l.addLayout(train_row)

        # Style Preset Group
        style_group = QGroupBox("Speech Style & Formatting Preset")
        s_layout = QVBoxLayout(style_group)
        self.style_combo = QComboBox()
        self.style_combo.addItem("Professional / Executive (Clean grammar, polished prose)", "professional")
        self.style_combo.addItem("Casual Chat (Conversational, messaging friendly)", "casual")
        self.style_combo.addItem("Developer / Code (Code tokens, identifiers, backticks)", "code")
        self.style_combo.addItem("Raw Cleaned (Verbatim, stutter removal only)", "raw")
        self.style_combo.addItem("Custom Persona (Your custom prompt guidelines below)", "custom")

        cur_style = self.profile.get("active_style", "professional")
        for i in range(self.style_combo.count()):
            if self.style_combo.itemData(i) == cur_style:
                self.style_combo.setCurrentIndex(i)
                break
        s_layout.addWidget(self.style_combo)

        self.app_aware_check = QCheckBox("App-Aware Styles (Auto-switch: Code in IDEs, Casual in Chat, Formal in Word)")
        self.app_aware_check.setStyleSheet("color: #f8fafc; font-size: 12px;")
        self.app_aware_check.setChecked(self.profile.get("app_aware_enabled", True))
        s_layout.addWidget(self.app_aware_check)
        l.addWidget(style_group)

        # Ollama LLM Group
        ollama_group = QGroupBox("Local LLM Stylist (Ollama)")
        o_layout = QVBoxLayout(ollama_group)

        o_top = QHBoxLayout()
        self.ollama_enable_check = QCheckBox("Enable Local LLM Rewriting")
        self.ollama_enable_check.setChecked(self.profile.get("ollama_enabled", True))
        o_top.addWidget(self.ollama_enable_check)

        self.test_ollama_btn = QPushButton("Test Connection")
        self.test_ollama_btn.setObjectName("secondaryBtn")
        self.test_ollama_btn.clicked.connect(self._test_ollama)
        o_top.addWidget(self.test_ollama_btn)
        o_layout.addLayout(o_top)

        model_row = QHBoxLayout()
        model_lbl = QLabel("Ollama Model:")
        model_row.addWidget(model_lbl)
        self.ollama_model_combo = QComboBox()
        cur_ollama_model = self.profile.get("ollama_model", "qwen3.5:9b-q4_K_M")
        self.ollama_model_combo.addItem(cur_ollama_model, cur_ollama_model)

        def _fetch_models():
            models = StyleEngine.list_installed_models()
            if models:
                def _update_ui():
                    self.ollama_model_combo.clear()
                    for m in models:
                        self.ollama_model_combo.addItem(m, m)
                    idx = self.ollama_model_combo.findData(cur_ollama_model)
                    if idx >= 0:
                        self.ollama_model_combo.setCurrentIndex(idx)
                QTimer.singleShot(0, _update_ui)

        threading.Thread(target=_fetch_models, daemon=True).start()

        model_row.addWidget(self.ollama_model_combo)
        o_layout.addLayout(model_row)
        l.addWidget(ollama_group)

        # Custom Persona Text
        persona_lbl = QLabel("Custom Persona Instructions (for 'Custom Persona' style):")
        persona_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        l.addWidget(persona_lbl)
        self.persona_edit = QTextEdit()
        self.persona_edit.setFixedHeight(70)
        self.persona_edit.setPlainText(self.profile.get("custom_persona_prompt", ""))
        l.addWidget(self.persona_edit)

        return tab

    def _create_dictionary_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setSpacing(12)

        # Custom Vocabulary Words
        vocab_group = QGroupBox("Custom Vocabulary & Names (Primes Whisper Token Decoder)")
        v_layout = QVBoxLayout(vocab_group)
        
        add_w_row = QHBoxLayout()
        self.new_word_input = QLineEdit()
        self.new_word_input.setPlaceholderText("Enter name or technical term (e.g. Soham, OpenCode, PySide6)...")
        add_w_row.addWidget(self.new_word_input)

        add_w_btn = QPushButton("Add Word")
        add_w_btn.clicked.connect(self._add_custom_word)
        add_w_row.addWidget(add_w_btn)
        v_layout.addLayout(add_w_row)

        self.vocab_list = QListWidget()
        self.vocab_list.setFixedHeight(120)
        self._refresh_vocab_list()
        v_layout.addWidget(self.vocab_list)

        del_w_btn = QPushButton("Remove Selected Word")
        del_w_btn.setObjectName("secondaryBtn")
        del_w_btn.clicked.connect(self._remove_custom_word)
        v_layout.addWidget(del_w_btn)
        l.addWidget(vocab_group)

        # Phonetic Word Replacements
        rep_group = QGroupBox("Phonetic & Word Replacements (Instant Auto-Correct)")
        r_layout = QVBoxLayout(rep_group)

        add_r_row = QHBoxLayout()
        self.rep_heard_input = QLineEdit()
        self.rep_heard_input.setPlaceholderText("When model hears...")
        add_r_row.addWidget(self.rep_heard_input)

        self.rep_target_input = QLineEdit()
        self.rep_target_input.setPlaceholderText("Replace with...")
        add_r_row.addWidget(self.rep_target_input)

        add_r_btn = QPushButton("Add Rule")
        add_r_btn.clicked.connect(self._add_replacement_rule)
        add_r_row.addWidget(add_r_btn)
        r_layout.addLayout(add_r_row)

        self.rep_table = QTableWidget(0, 2)
        self.rep_table.setHorizontalHeaderLabels(["When Heard", "Replace With"])
        self.rep_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.rep_table.setFixedHeight(120)
        self._refresh_rep_table()
        r_layout.addWidget(self.rep_table)

        del_r_btn = QPushButton("Remove Selected Rule")
        del_r_btn.setObjectName("secondaryBtn")
        del_r_btn.clicked.connect(self._remove_replacement_rule)
        r_layout.addWidget(del_r_btn)
        l.addWidget(rep_group)

        return tab

    def _refresh_vocab_list(self):
        self.vocab_list.clear()
        for w in self.profile_mgr.get_custom_words():
            self.vocab_list.addItem(w)

    def _add_custom_word(self):
        w = self.new_word_input.text().strip()
        if w:
            self.profile_mgr.add_custom_word(w)
            self.new_word_input.clear()
            self._refresh_vocab_list()

    def _remove_custom_word(self):
        sel = self.vocab_list.currentItem()
        if sel:
            self.profile_mgr.remove_custom_word(sel.text())
            self._refresh_vocab_list()

    def _refresh_rep_table(self):
        reps = self.profile_mgr.get_replacements()
        self.rep_table.setRowCount(len(reps))
        for row, (h, t) in enumerate(reps.items()):
            self.rep_table.setItem(row, 0, QTableWidgetItem(h))
            self.rep_table.setItem(row, 1, QTableWidgetItem(t))

    def _add_replacement_rule(self):
        h = self.rep_heard_input.text().strip()
        t = self.rep_target_input.text().strip()
        if h and t:
            self.profile_mgr.add_replacement(h, t)
            self.rep_heard_input.clear()
            self.rep_target_input.clear()
            self._refresh_rep_table()

    def _remove_replacement_rule(self):
        cur_row = self.rep_table.currentRow()
        if cur_row >= 0:
            item = self.rep_table.item(cur_row, 0)
            if item:
                self.profile_mgr.remove_replacement(item.text())
                self._refresh_rep_table()

    def _test_ollama(self):
        models = StyleEngine.list_installed_models()
        if models:
            QMessageBox.information(self, "Ollama Connected", f"Successfully connected to Ollama!\nInstalled models: {', '.join(models)}")
        else:
            QMessageBox.warning(self, "Ollama Notice", "Could not reach Ollama at http://127.0.0.1:11434.\nMake sure the Ollama application is running.")

    def _launch_web_studio(self):
        import webbrowser
        import subprocess
        import socket
        import sys

        is_running = False
        try:
            with socket.create_connection(("127.0.0.1", 8000), timeout=0.2):
                is_running = True
        except Exception:
            is_running = False

        if not is_running:
            server_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studio_server.py")
            if os.path.exists(server_script):
                python_exe = sys.executable
                subprocess.Popen([python_exe, server_script], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                time.sleep(0.4)

        webbrowser.open("http://127.0.0.1:8000")

    def _launch_wizard(self):
        from ui.voice_training_dialog import VoiceTrainingDialog
        wiz = VoiceTrainingDialog(self.audio_engine, self.whisper_engine, self)
        if wiz.exec():
            self._refresh_vocab_list()
            self._refresh_rep_table()

    def _save_and_accept(self):
        # General
        self.config["model_name"] = self.model_combo.currentData()
        self.config["input_device_index"] = self.device_combo.currentData()
        self.config["auto_show_on_textbox"] = self.auto_show_check.isChecked()
        self.config["groq_api_key"] = self.groq_key_input.text().strip()
        if self.whisper_engine:
            self.whisper_engine.groq_api_key = self.config["groq_api_key"]

        # Voice & Styles
        self.profile["active_style"] = self.style_combo.currentData()
        self.profile["app_aware_enabled"] = self.app_aware_check.isChecked()
        self.profile["ollama_enabled"] = self.ollama_enable_check.isChecked()
        self.profile["ollama_model"] = self.ollama_model_combo.currentData()
        self.profile["custom_persona_prompt"] = self.persona_edit.toPlainText().strip()
        self.profile_mgr.save_profile()

        self.accept()
