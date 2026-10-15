import os
import time
import threading
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QGroupBox, QTabWidget, QWidget, QCheckBox,
    QLineEdit, QListWidget, QListWidgetItem, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QColor
from voice_profile import VoiceProfileManager
from style_engine import StyleEngine
from ui.theme_helper import apply_dark_window_attributes


class WordRowWidget(QWidget):
    """Modern interactive row for a custom vocabulary word with an instant delete button."""
    def __init__(self, word: str, on_remove_callback, parent=None):
        super().__init__(parent)
        self.word = word
        self.on_remove_callback = on_remove_callback

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 8, 5)
        layout.setSpacing(10)

        # Bullet indicator + word label
        self.lbl = QLabel(f"•  {word}")
        self.lbl.setStyleSheet("color: #f1f5f9; font-size: 13px; font-weight: 600;")
        layout.addWidget(self.lbl)
        layout.addStretch()

        # Delete button
        self.del_btn = QPushButton("Remove")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f87171;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
                color: white;
                border-color: #ef4444;
            }
        """)
        self.del_btn.clicked.connect(lambda: self.on_remove_callback(self.word))
        layout.addWidget(self.del_btn)


class ReplacementRowWidget(QWidget):
    """Modern interactive row for phonetic replacements with an instant delete button."""
    def __init__(self, heard: str, target: str, on_remove_callback, parent=None):
        super().__init__(parent)
        self.heard = heard
        self.target = target
        self.on_remove_callback = on_remove_callback

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 8, 5)
        layout.setSpacing(10)

        # Heard bubble
        heard_lbl = QLabel(heard)
        heard_lbl.setStyleSheet("""
            background-color: #0f172a;
            color: #93c5fd;
            border: 1px solid #334155;
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 12px;
            font-family: 'Consolas', monospace;
        """)
        layout.addWidget(heard_lbl)

        # Arrow
        arrow_lbl = QLabel("→")
        arrow_lbl.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px;")
        layout.addWidget(arrow_lbl)

        # Target bubble
        target_lbl = QLabel(target)
        target_lbl.setStyleSheet("""
            background-color: #0f172a;
            color: #34d399;
            border: 1px solid #334155;
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 12px;
            font-weight: bold;
        """)
        layout.addWidget(target_lbl)
        layout.addStretch()

        # Delete button
        self.del_btn = QPushButton("Remove")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f87171;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
                color: white;
                border-color: #ef4444;
            }
        """)
        self.del_btn.clicked.connect(lambda: self.on_remove_callback(self.heard))
        layout.addWidget(self.del_btn)


class SettingsDialog(QDialog):
    def __init__(self, config, audio_engine, whisper_engine=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.audio_engine = audio_engine
        self.whisper_engine = whisper_engine
        self.profile_mgr = VoiceProfileManager.get_instance()
        self.profile = self.profile_mgr.profile

        self.setWindowTitle("Whisper Flow - Preferences")
        self.setFixedSize(620, 680)

        # Eliminate white flash and enable native dark title bar immediately
        apply_dark_window_attributes(self)

        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 13px;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                background-color: #111827;
                padding: 14px;
            }
            QTabBar::tab {
                background: #1e293b;
                color: #94a3b8;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 9px 20px;
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
                padding-top: 14px;
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
                padding: 7px 12px;
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
                color: #e2e8f0;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #475569;
            }
            QPushButton#actionBtn {
                background-color: #4f46e5;
                color: white;
            }
            QPushButton#actionBtn:hover {
                background-color: #4338ca;
            }
            QLineEdit, QTextEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #3b82f6;
            }
            QListWidget {
                background-color: #0b0f19;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                border-bottom: 1px solid #1e293b;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #161e2e;
            }
            QScrollBar:vertical {
                border: none;
                background: #0f172a;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #475569;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Title
        title_label = QLabel("Whisper Flow Preferences")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
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

        self._dictionary_loaded = False
        self.tabs.currentChanged.connect(self._on_tab_changed)
        QTimer.singleShot(0, self._ensure_dictionary_loaded)

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

        # Focus Behavior
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

        info_label = QLabel("Global Shortcut: Ctrl + Shift + Space\nAutomatically types directly into your active text box.")
        info_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-style: italic;")
        l.addWidget(info_label)
        l.addStretch()

        return tab

    def _create_voice_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setSpacing(12)

        # Web Voice Studio (100 Sentences) Banner Card
        studio_group = QGroupBox("Web Voice Studio (Bilingual Calibration)")
        s_card = QVBoxLayout(studio_group)
        studio_desc = QLabel("Read 100 curated English & Hindi/Hinglish sentences in your browser to tune recognition accuracy and add custom words with 1 click.")
        studio_desc.setWordWrap(True)
        studio_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        s_card.addWidget(studio_desc)

        s_btn_row = QHBoxLayout()
        s_btn_row.addStretch()
        self.studio_btn = QPushButton("Open Web Voice Studio (Port 8000)")
        self.studio_btn.setObjectName("actionBtn")
        self.studio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.studio_btn.clicked.connect(self._launch_web_studio)
        s_btn_row.addWidget(self.studio_btn)
        s_card.addLayout(s_btn_row)
        l.addWidget(studio_group)

        # Acoustic Calibration Wizard
        train_group = QGroupBox("Acoustic Calibration Wizard")
        t_card = QVBoxLayout(train_group)
        train_desc = QLabel("Calibrate microphone gain, background room noise floor, and average speaking pace (WPM).")
        train_desc.setWordWrap(True)
        train_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        t_card.addWidget(train_desc)

        t_btn_row = QHBoxLayout()
        t_btn_row.addStretch()
        self.wizard_btn = QPushButton("Run Calibration Wizard")
        self.wizard_btn.setObjectName("secondaryBtn")
        self.wizard_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wizard_btn.clicked.connect(self._launch_wizard)
        t_btn_row.addWidget(self.wizard_btn)
        t_card.addLayout(t_btn_row)
        l.addWidget(train_group)

        # Speech Style & Formatting Preset
        style_group = QGroupBox("Speech Style & Formatting Preset")
        s_layout = QVBoxLayout(style_group)
        self.style_combo = QComboBox()
        self.style_combo.addItem("Professional / Executive (Clean grammar, polished prose)", "professional")
        self.style_combo.addItem("Casual Chat (Zero punctuation, lowercase natural chat)", "casual")
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

        # Local LLM Stylist (Ollama)
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
        self.persona_edit.setFixedHeight(60)
        self.persona_edit.setPlainText(self.profile.get("custom_persona_prompt", ""))
        l.addWidget(self.persona_edit)

        return tab

    def _create_dictionary_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setSpacing(14)

        # 1. Custom Vocabulary Section
        vocab_group = QGroupBox("Custom Vocabulary & Names (Primes Whisper Token Decoder)")
        v_layout = QVBoxLayout(vocab_group)
        v_layout.setSpacing(8)

        # Add Row
        add_w_row = QHBoxLayout()
        self.new_word_input = QLineEdit()
        self.new_word_input.setPlaceholderText("Type name or jargon (e.g. Soham, OpenCode, PySide6) and press Enter...")
        self.new_word_input.returnPressed.connect(self._add_custom_word)
        add_w_row.addWidget(self.new_word_input)

        add_w_btn = QPushButton("+ Add Word")
        add_w_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_w_btn.clicked.connect(self._add_custom_word)
        add_w_row.addWidget(add_w_btn)
        v_layout.addLayout(add_w_row)

        # Search filter + count header
        v_meta_row = QHBoxLayout()
        self.vocab_filter_input = QLineEdit()
        self.vocab_filter_input.setPlaceholderText("Filter words...")
        self.vocab_filter_input.textChanged.connect(self._filter_vocab_list)
        v_meta_row.addWidget(self.vocab_filter_input)

        self.vocab_count_lbl = QLabel("0 saved")
        self.vocab_count_lbl.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        v_meta_row.addWidget(self.vocab_count_lbl)
        v_layout.addLayout(v_meta_row)

        # Custom List with 1-click delete buttons
        self.vocab_list = QListWidget()
        self.vocab_list.setFixedHeight(140)
        v_layout.addWidget(self.vocab_list)
        l.addWidget(vocab_group)

        # 2. Phonetic Replacements Section
        rep_group = QGroupBox("Phonetic & Word Replacements (Instant Auto-Correct)")
        r_layout = QVBoxLayout(rep_group)
        r_layout.setSpacing(8)

        add_r_row = QHBoxLayout()
        self.rep_heard_input = QLineEdit()
        self.rep_heard_input.setPlaceholderText("When model hears (e.g. pie side)...")
        self.rep_heard_input.returnPressed.connect(self._add_replacement_rule)
        add_r_row.addWidget(self.rep_heard_input)

        arrow_icon = QLabel("→")
        arrow_icon.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px;")
        add_r_row.addWidget(arrow_icon)

        self.rep_target_input = QLineEdit()
        self.rep_target_input.setPlaceholderText("Replace with (e.g. PySide6)...")
        self.rep_target_input.returnPressed.connect(self._add_replacement_rule)
        add_r_row.addWidget(self.rep_target_input)

        add_r_btn = QPushButton("+ Add Rule")
        add_r_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_r_btn.clicked.connect(self._add_replacement_rule)
        add_r_row.addWidget(add_r_btn)
        r_layout.addLayout(add_r_row)

        # Search filter + count header
        r_meta_row = QHBoxLayout()
        self.rep_filter_input = QLineEdit()
        self.rep_filter_input.setPlaceholderText("Filter rules...")
        self.rep_filter_input.textChanged.connect(self._filter_rep_list)
        r_meta_row.addWidget(self.rep_filter_input)

        self.rep_count_lbl = QLabel("0 rules active")
        self.rep_count_lbl.setStyleSheet("color: #34d399; font-weight: bold; font-size: 12px;")
        r_meta_row.addWidget(self.rep_count_lbl)
        r_layout.addLayout(r_meta_row)

        # Custom List with 1-click delete buttons
        self.rep_list = QListWidget()
        self.rep_list.setFixedHeight(140)
        r_layout.addWidget(self.rep_list)
        l.addWidget(rep_group)

        # Deferred population: loaded lazily on tab switch or singleShot tick
        return tab

    def showEvent(self, event):
        super().showEvent(event)
        try:
            import ctypes
            ctypes.windll.user32.ReleaseCapture()
        except Exception:
            pass

    def _on_tab_changed(self, index: int):
        if index == 2:  # Personal Dictionary tab
            self._ensure_dictionary_loaded()

    def _ensure_dictionary_loaded(self):
        if getattr(self, '_dictionary_loaded', False):
            return
        self._dictionary_loaded = True
        self._refresh_vocab_list()
        self._refresh_rep_list()

    def _refresh_vocab_list(self):
        self._dictionary_loaded = True
        filter_text = getattr(self, 'vocab_filter_input', None)
        query = filter_text.text().strip().lower() if filter_text else ""
        self.vocab_list.clear()

        all_words = self.profile_mgr.get_custom_words()
        for w in all_words:
            item = QListWidgetItem(self.vocab_list)
            item.setSizeHint(QSize(0, 36))
            row_widget = WordRowWidget(w, on_remove_callback=self._on_remove_word_clicked)
            self.vocab_list.setItemWidget(item, row_widget)
            if query and query not in w.lower():
                item.setHidden(True)

        if hasattr(self, 'vocab_count_lbl'):
            self.vocab_count_lbl.setText(f"{len(all_words)} saved")

    def _filter_vocab_list(self):
        self._ensure_dictionary_loaded()
        filter_text = getattr(self, 'vocab_filter_input', None)
        query = filter_text.text().strip().lower() if filter_text else ""
        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            widget = self.vocab_list.itemWidget(item)
            if widget and hasattr(widget, "word"):
                matches = not query or query in widget.word.lower()
                item.setHidden(not matches)

    def _add_custom_word(self):
        w = self.new_word_input.text().strip()
        if w:
            self.profile_mgr.add_custom_word(w)
            self.new_word_input.clear()
            self._ensure_dictionary_loaded()
            item = QListWidgetItem(self.vocab_list)
            item.setSizeHint(QSize(0, 36))
            row_widget = WordRowWidget(w, on_remove_callback=self._on_remove_word_clicked)
            self.vocab_list.setItemWidget(item, row_widget)
            all_words = self.profile_mgr.get_custom_words()
            if hasattr(self, 'vocab_count_lbl'):
                self.vocab_count_lbl.setText(f"{len(all_words)} saved")
            query = self.vocab_filter_input.text().strip().lower() if hasattr(self, 'vocab_filter_input') else ""
            if query and query not in w.lower():
                item.setHidden(True)

    def _on_remove_word_clicked(self, word: str):
        self.profile_mgr.remove_custom_word(word)
        # 1-Click Instant Removal: delete row in-place via takeItem (0ms) without rebuilding entire list
        for i in range(self.vocab_list.count()):
            item = self.vocab_list.item(i)
            widget = self.vocab_list.itemWidget(item)
            if widget and getattr(widget, "word", None) == word:
                taken = self.vocab_list.takeItem(i)
                del taken
                break
        all_words = self.profile_mgr.get_custom_words()
        if hasattr(self, 'vocab_count_lbl'):
            self.vocab_count_lbl.setText(f"{len(all_words)} saved")

    def _refresh_rep_list(self):
        self._dictionary_loaded = True
        filter_text = getattr(self, 'rep_filter_input', None)
        query = filter_text.text().strip().lower() if filter_text else ""
        self.rep_list.clear()

        reps = self.profile_mgr.get_replacements()
        for h, t in reps.items():
            item = QListWidgetItem(self.rep_list)
            item.setSizeHint(QSize(0, 38))
            row_widget = ReplacementRowWidget(h, t, on_remove_callback=self._on_remove_rep_clicked)
            self.rep_list.setItemWidget(item, row_widget)
            if query and (query not in h.lower() and query not in t.lower()):
                item.setHidden(True)

        if hasattr(self, 'rep_count_lbl'):
            self.rep_count_lbl.setText(f"{len(reps)} rules active")

    def _filter_rep_list(self):
        self._ensure_dictionary_loaded()
        filter_text = getattr(self, 'rep_filter_input', None)
        query = filter_text.text().strip().lower() if filter_text else ""
        for i in range(self.rep_list.count()):
            item = self.rep_list.item(i)
            widget = self.rep_list.itemWidget(item)
            if widget and hasattr(widget, "heard"):
                matches = not query or (query in widget.heard.lower() or query in getattr(widget, "target", "").lower())
                item.setHidden(not matches)

    def _add_replacement_rule(self):
        h = self.rep_heard_input.text().strip()
        t = self.rep_target_input.text().strip()
        if h and t:
            self.profile_mgr.add_replacement(h, t)
            self.rep_heard_input.clear()
            self.rep_target_input.clear()
            self._ensure_dictionary_loaded()
            item = QListWidgetItem(self.rep_list)
            item.setSizeHint(QSize(0, 38))
            row_widget = ReplacementRowWidget(h, t, on_remove_callback=self._on_remove_rep_clicked)
            self.rep_list.setItemWidget(item, row_widget)
            reps = self.profile_mgr.get_replacements()
            if hasattr(self, 'rep_count_lbl'):
                self.rep_count_lbl.setText(f"{len(reps)} rules active")
            query = self.rep_filter_input.text().strip().lower() if hasattr(self, 'rep_filter_input') else ""
            if query and (query not in h.lower() and query not in t.lower()):
                item.setHidden(True)

    def _on_remove_rep_clicked(self, heard: str):
        self.profile_mgr.remove_replacement(heard)
        # 1-Click Instant Removal: delete row in-place via takeItem (0ms) without rebuilding entire list
        for i in range(self.rep_list.count()):
            item = self.rep_list.item(i)
            widget = self.rep_list.itemWidget(item)
            if widget and getattr(widget, "heard", None) == heard:
                taken = self.rep_list.takeItem(i)
                del taken
                break
        reps = self.profile_mgr.get_replacements()
        if hasattr(self, 'rep_count_lbl'):
            self.rep_count_lbl.setText(f"{len(reps)} rules active")

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
        try:
            import ctypes
            ctypes.windll.user32.ReleaseCapture()
        except Exception:
            pass
        from ui.voice_training_dialog import VoiceTrainingDialog
        wiz = VoiceTrainingDialog(self.audio_engine, self.whisper_engine, self)
        if wiz.exec():
            self._refresh_vocab_list()
            self._refresh_rep_list()

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
