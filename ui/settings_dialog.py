import os
import time
import threading
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, 
    QPushButton, QGroupBox, QTabWidget, QWidget, QCheckBox,
    QLineEdit, QListWidget, QListWidgetItem, QTextEdit, QMessageBox,
    QProgressBar
)
from PySide6.QtCore import Qt, QTimer, QSize, Signal, Slot
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
        self.del_btn.setObjectName("removeBtn")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.del_btn.setObjectName("removeBtn")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.clicked.connect(lambda: self.on_remove_callback(self.heard))
        layout.addWidget(self.del_btn)



DIALOG_STYLE = """
    QDialog {
        background-color: #0f172a;
        color: #f8fafc;
        font-family: 'Segoe UI', -apple-system, sans-serif;
    }
    QLabel {
        color: #cbd5e1;
        font-size: 13px;
    }
    EngineCard {
        background-color: #111827;
        border: 1px solid #334155;
        border-radius: 8px;
    }
    EngineCard[selected="true"] {
        background-color: #1e293b;
        border: 2px solid #3b82f6;
        border-radius: 8px;
    }
    StyleCard {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
    }
    StyleCard[selected="true"] {
        background-color: #1e293b;
        border: 2px solid #8b5cf6;
        border-radius: 8px;
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
    QPushButton#removeBtn {
        background-color: #1e293b;
        color: #f87171;
        border: 1px solid #475569;
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: bold;
    }
    QPushButton#removeBtn:hover {
        background-color: #dc2626;
        color: white;
        border-color: #ef4444;
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
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
"""


class EngineCard(QWidget):
    clicked = Signal(str)

    def __init__(self, mode: str, title: str, subtitle: str, badge: str = "", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.title_text = title
        self.subtitle_text = subtitle
        self.badge_text = badge
        self._selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(76)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #f8fafc; border: none; background: transparent;")
        header_row.addWidget(self.title_lbl)
        header_row.addStretch()

        if badge:
            self.badge_lbl = QLabel(badge)
            header_row.addWidget(self.badge_lbl)
        else:
            self.badge_lbl = None
        layout.addLayout(header_row)

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setWordWrap(True)
        self.sub_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; border: none; background: transparent; line-height: 1.25;")
        layout.addWidget(self.sub_lbl)

        self._update_style()

    def set_selected(self, selected: bool):
        if getattr(self, "_selected", None) == selected:
            return
        self._selected = selected
        self._update_style()

    def _update_style(self):
        self.setProperty("selected", "true" if self._selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if self.badge_lbl:
            if self._selected:
                self.badge_lbl.setStyleSheet("background-color: #2563eb; color: #ffffff; border: none; border-radius: 4px; padding: 2px 7px; font-size: 10px; font-weight: bold;")
            else:
                self.badge_lbl.setStyleSheet("background-color: rgba(148, 163, 184, 0.15); color: #94a3b8; border: none; border-radius: 4px; padding: 2px 7px; font-size: 10px; font-weight: bold;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.mode)


class StyleCard(QWidget):
    clicked = Signal(str)

    def __init__(self, key: str, title: str, subtitle: str, badge: str = "0ms • Zero GPU", parent=None):
        super().__init__(parent)
        self.key = key
        self.title_text = title
        self.subtitle_text = subtitle
        self.badge_text = badge
        self._selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #f8fafc; border: none; background: transparent;")
        top_row.addWidget(self.title_lbl)
        top_row.addStretch()

        self.check_lbl = QLabel("")
        self.check_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #34d399; border: none; background: transparent;")
        top_row.addWidget(self.check_lbl)
        layout.addLayout(top_row)

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setWordWrap(True)
        self.sub_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; border: none; background: transparent; line-height: 1.25;")
        layout.addWidget(self.sub_lbl)

        layout.addStretch()

        self.badge_lbl = QLabel(badge)
        self.badge_lbl.setStyleSheet("font-size: 9px; color: #38bdf8; font-weight: 600; border: none; background: transparent;")
        layout.addWidget(self.badge_lbl)

        self._update_style()

    def set_selected(self, selected: bool):
        if getattr(self, "_selected", None) == selected:
            return
        self._selected = selected
        self.check_lbl.setText("✓" if selected else "")
        self._update_style()

    def _update_style(self):
        self.setProperty("selected", "true" if self._selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)


class SettingsDialog(QDialog):
    engine_changed = Signal(str)
    style_changed = Signal(str)
    language_changed = Signal(str)
    _api_test_result_signal = Signal(bool, str)

    def __init__(self, config, audio_engine, whisper_engine=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.audio_engine = audio_engine
        self.whisper_engine = whisper_engine
        self.profile_mgr = VoiceProfileManager.get_instance()
        self.profile = self.profile_mgr.profile

        self._api_test_result_signal.connect(self._on_api_test_result)
        self._test_stream_active = False

        self.setWindowTitle("Whisper Flow - Preferences")
        self.setFixedSize(640, 720)

        # Eliminate white flash and enable native dark title bar immediately
        apply_dark_window_attributes(self)

        self.setStyleSheet(DIALOG_STYLE)

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
        self.tabs.addTab(self.tab_general, "General")

        self._container_voice = QWidget()
        self._layout_voice = QVBoxLayout(self._container_voice)
        self._layout_voice.setContentsMargins(0, 0, 0, 0)
        self._voice_attached = False
        self.tabs.addTab(self._container_voice, "Voice & Styles")

        self._container_dict = QWidget()
        self._layout_dict = QVBoxLayout(self._container_dict)
        self._layout_dict.setContentsMargins(0, 0, 0, 0)
        self._dict_attached = False
        self._dictionary_loaded = False
        self.tabs.addTab(self._container_dict, "Personal Dictionary")
        layout.addWidget(self.tabs)

        self.tabs.currentChanged.connect(self._on_tab_changed)

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
        l.setSpacing(12)

        # 1. Engine Selector Toggle Cards (Groq Cloud vs Local CPU)
        engine_group = QGroupBox("Engine Selector (Speech-to-Text Architecture)")
        eng_layout = QVBoxLayout(engine_group)
        eng_layout.setSpacing(8)

        self.card_groq = EngineCard(
            "groq",
            "Groq Cloud (whisper-large-v3-turbo)",
            "Sub-150ms speech-to-text • 0% CPU & GPU VRAM • Groq Cloud API",
            "RECOMMENDED"
        )
        self.card_local = EngineCard(
            "local",
            "Local CPU (Offline)",
            "Private offline int8 quantized Whisper • Zero cloud calls • 100% local on device",
            "OFFLINE"
        )

        self.card_groq.clicked.connect(self._on_engine_card_clicked)
        self.card_local.clicked.connect(self._on_engine_card_clicked)

        eng_layout.addWidget(self.card_groq)
        eng_layout.addWidget(self.card_local)
        l.addWidget(engine_group)

        # Initialize active engine card
        current_engine = self.config.get("engine_mode", "groq")
        self._set_engine_mode(current_engine, emit_signal=False)

        # 2. Local Whisper Model (Offline Mode - Fast Models Only)
        model_group = QGroupBox("Local Whisper Model (Offline Mode)")
        m_layout = QVBoxLayout(model_group)
        self.model_combo = QComboBox()
        models = [
            ("base.en - Ultra-Fast English (~50ms)", "base.en"),
            ("base - Fast Multilingual / Hindi (~60ms)", "base"),
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

        # 3. Microphone Input & Live VU Meter Diagnostics
        audio_group = QGroupBox("Microphone Input & Live Audio Diagnostics")
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

        vu_row = QHBoxLayout()
        vu_lbl = QLabel("Live Mic Input:")
        vu_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
        vu_row.addWidget(vu_lbl)

        self.vu_meter = QProgressBar()
        self.vu_meter.setRange(0, 100)
        self.vu_meter.setValue(0)
        self.vu_meter.setTextVisible(False)
        self.vu_meter.setFixedHeight(12)
        self.vu_meter.setStyleSheet("""
            QProgressBar {
                background-color: #0b0f19;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #38bdf8);
                border-radius: 5px;
            }
        """)
        vu_row.addWidget(self.vu_meter)
        a_layout.addLayout(vu_row)
        l.addWidget(audio_group)

        # 4. Groq API Key & Live Connection Test
        groq_group = QGroupBox("Cloud Speech Fallback (Groq API Key & Live Connection)")
        g_layout = QVBoxLayout(groq_group)
        self.groq_key_input = QLineEdit()
        self.groq_key_input.setPlaceholderText("Enter Groq API Key (gsk_...) for 0% CPU cloud Whisper")
        self.groq_key_input.setText(self.config.get("groq_api_key", ""))
        self.groq_key_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        g_layout.addWidget(self.groq_key_input)

        test_row = QHBoxLayout()
        test_row.setSpacing(12)
        test_row.setContentsMargins(0, 4, 0, 4)
        self.test_conn_btn = QPushButton("Test Mic & API Connection")
        self.test_conn_btn.setObjectName("secondaryBtn")
        self.test_conn_btn.setMinimumHeight(34)
        self.test_conn_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_conn_btn.clicked.connect(self._on_test_connection_clicked)
        test_row.addWidget(self.test_conn_btn)

        self.conn_status_lbl = QLabel("Ready to test")
        self.conn_status_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        test_row.addWidget(self.conn_status_lbl)
        test_row.addStretch()
        g_layout.addLayout(test_row)

        l.addWidget(groq_group)

        # 5. Focus Behavior
        behavior_group = QGroupBox("Focus Behavior")
        b_layout = QVBoxLayout(behavior_group)
        self.auto_show_check = QCheckBox("Show widget only when clicking into a text box")
        self.auto_show_check.setStyleSheet("color: #f8fafc; font-size: 13px;")
        self.auto_show_check.setChecked(self.config.get("auto_show_on_textbox", True))
        b_layout.addWidget(self.auto_show_check)
        l.addWidget(behavior_group)

        info_label = QLabel("Global Shortcut: Ctrl + Shift + Space • Automatically types directly into active app.")
        info_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        l.addWidget(info_label)
        l.addStretch()

        return tab

    def _create_voice_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setSpacing(12)

        # 1. 2x2 Speech Style Selection Cards
        style_group = QGroupBox("Speech Style (Instant Zero-GPU Transformations)")
        s_layout = QVBoxLayout(style_group)
        s_layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.card_casual = StyleCard(
            "casual",
            "Casual Chat",
            "Strips trailing periods, commas & robotic casing. Natural conversation.",
            "0ms • Zero GPU"
        )
        self.card_developer = StyleCard(
            "developer",
            "Developer Mode",
            "Transforms spoken commands into camelCase, snake_case & code syntax.",
            "0ms • Zero GPU"
        )
        self.card_professional = StyleCard(
            "professional",
            "Professional",
            "Clean grammar, polished executive prose, and formatted numbers.",
            "0ms • Zero GPU"
        )
        self.card_custom = StyleCard(
            "custom",
            "Custom Persona",
            "Formats output to match custom user-defined tone without adding latency.",
            "0ms • Zero GPU"
        )

        self.style_cards = {
            "casual": self.card_casual,
            "developer": self.card_developer,
            "code": self.card_developer,
            "professional": self.card_professional,
            "custom": self.card_custom
        }

        self.card_casual.clicked.connect(lambda: self._select_style("casual"))
        self.card_developer.clicked.connect(lambda: self._select_style("developer"))
        self.card_professional.clicked.connect(lambda: self._select_style("professional"))
        self.card_custom.clicked.connect(lambda: self._select_style("custom"))

        grid.addWidget(self.card_casual, 0, 0)
        grid.addWidget(self.card_developer, 0, 1)
        grid.addWidget(self.card_professional, 1, 0)
        grid.addWidget(self.card_custom, 1, 1)
        s_layout.addLayout(grid)

        # Spacing to ensure separation between style cards and options
        s_layout.addSpacing(8)

        # Backward compatibility combo box (hidden)
        self.style_combo = QComboBox()
        self.style_combo.addItem("Casual Chat", "casual")
        self.style_combo.addItem("Developer / Code", "developer")
        self.style_combo.addItem("Professional / Executive", "professional")
        self.style_combo.addItem("Custom Persona", "custom")
        self.style_combo.setVisible(False)
        s_layout.addWidget(self.style_combo)

        # Highlight current style
        cur_style = self.profile.get("active_style", "professional")
        self._select_style(cur_style, emit_signal=False)

        self.app_aware_check = QCheckBox("App-Aware Styles (Auto-switch: Code in IDEs, Casual in Chat, Formal in Word)")
        self.app_aware_check.setStyleSheet("color: #f8fafc; font-size: 12px; margin-top: 4px;")
        self.app_aware_check.setChecked(self.profile.get("app_aware_enabled", True))
        s_layout.addWidget(self.app_aware_check)
        l.addWidget(style_group)

        # 2. Web Voice Studio (100 Sentences) Banner Card
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

        # 3. Acoustic Calibration Wizard
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

        # 4. Custom Persona Text
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

    def _ensure_voice_tab(self):
        if not getattr(self, "_voice_attached", False):
            self._voice_attached = True
            self.tab_voice = self._create_voice_tab()
            self._layout_voice.addWidget(self.tab_voice)
        return getattr(self, "tab_voice", None)

    def _ensure_dictionary_tab(self):
        if not getattr(self, "_dict_attached", False):
            self._dict_attached = True
            self.tab_dictionary = self._create_dictionary_tab()
            self._layout_dict.addWidget(self.tab_dictionary)
        return getattr(self, "tab_dictionary", None)

    def __getattr__(self, name):
        if name in (
            "tab_voice", "card_casual", "card_developer", "card_professional", "card_custom",
            "style_cards", "style_combo", "app_aware_check", "studio_btn"
        ):
            self._ensure_voice_tab()
            if name in self.__dict__:
                return self.__dict__[name]
        elif name in (
            "tab_dictionary", "new_word_input", "vocab_filter_input", "vocab_count_lbl",
            "vocab_list", "rep_heard_input", "rep_target_input", "rep_filter_input",
            "rep_count_lbl", "rep_list"
        ):
            self._ensure_dictionary_tab()
            if name in self.__dict__:
                return self.__dict__[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def _on_tab_changed(self, index: int):
        if index == 1:
            self._ensure_voice_tab()
        elif index == 2:
            self._ensure_dictionary_tab()
            self._ensure_dictionary_loaded()

    def _ensure_dictionary_loaded(self):
        self._ensure_dictionary_tab()
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

    def _on_engine_card_clicked(self, mode: str):
        self._set_engine_mode(mode, emit_signal=True)

    def _set_engine_mode(self, mode: str, emit_signal: bool = True):
        self.engine_mode = mode
        self.config["engine_mode"] = mode
        if hasattr(self, "card_groq") and hasattr(self, "card_local"):
            self.card_groq.set_selected(mode == "groq")
            self.card_local.set_selected(mode == "local")
        if self.whisper_engine:
            self.whisper_engine.engine_mode = mode
        if emit_signal:
            self.engine_changed.emit(mode)

    def _select_style(self, style_key: str, emit_signal: bool = True):
        norm_key = "developer" if style_key in ("developer", "code", "dev") else style_key
        if hasattr(self, "card_casual"):
            self.card_casual.set_selected(norm_key == "casual")
        if hasattr(self, "card_developer"):
            self.card_developer.set_selected(norm_key == "developer")
        if hasattr(self, "card_professional"):
            self.card_professional.set_selected(norm_key == "professional")
        if hasattr(self, "card_custom"):
            self.card_custom.set_selected(norm_key == "custom")

        # Sync profile & combo box
        self.profile["active_style"] = norm_key
        if emit_signal:
            self.profile_mgr.set_active_style(norm_key)
        elif getattr(self.profile_mgr, "get_active_style", lambda: None)() != norm_key:
            self.profile_mgr.set_active_style(norm_key)
        if hasattr(self, "style_combo"):
            for i in range(self.style_combo.count()):
                if self.style_combo.itemData(i) in (norm_key, style_key):
                    self.style_combo.setCurrentIndex(i)
                    break

        if emit_signal:
            self.style_changed.emit(norm_key)

    def _on_test_connection_clicked(self):
        # 1. Start live VU meter
        self._start_audio_vu_test()
        # 2. Asynchronous Groq API ping
        self._start_groq_ping_test()

    def _start_audio_vu_test(self):
        if not hasattr(self, "_vu_timer"):
            self._vu_timer = QTimer(self)
            self._vu_timer.setInterval(40)
            self._vu_timer.timeout.connect(self._on_vu_tick)

        self._vu_end_time = time.time() + 5.0
        self._test_stream_active = False

        if self.audio_engine and not getattr(self.audio_engine, "is_recording", False):
            try:
                self.audio_engine.start_recording()
                self._test_stream_active = True
            except Exception as e:
                print(f"[SettingsDialog] Mic test stream error: {e}")

        self._vu_timer.start()

    def _on_vu_tick(self):
        if time.time() > getattr(self, "_vu_end_time", 0):
            self._stop_audio_vu_test()
            return

        vol = 0.0
        if self.audio_engine:
            try:
                vol = self.audio_engine.get_current_volume()
            except Exception:
                vol = 0.0
        pct = int(min(100, max(0, vol * 100)))
        if hasattr(self, "vu_meter"):
            self.vu_meter.setValue(pct)

    def _stop_audio_vu_test(self):
        if hasattr(self, "_vu_timer") and self._vu_timer.isActive():
            self._vu_timer.stop()
        if getattr(self, "_test_stream_active", False):
            self._test_stream_active = False
            if self.audio_engine and getattr(self.audio_engine, "is_recording", False):
                try:
                    self.audio_engine.stop_recording()
                except Exception:
                    pass
        if hasattr(self, "vu_meter"):
            self.vu_meter.setValue(0)

    def _start_groq_ping_test(self):
        groq_key = self.groq_key_input.text().strip()
        if not groq_key:
            self.conn_status_lbl.setText("Invalid Key (Key is empty)")
            self.conn_status_lbl.setStyleSheet("color: #f87171; font-weight: bold; font-size: 12px;")
            return

        self.conn_status_lbl.setText("Testing connection...")
        self.conn_status_lbl.setStyleSheet("color: #60a5fa; font-size: 12px;")
        self.test_conn_btn.setEnabled(False)

        def _worker():
            import urllib.request
            import urllib.error
            t0 = time.perf_counter()
            success = False
            message = ""
            try:
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/models",
                    headers={
                        "Authorization": f"Bearer {groq_key}",
                        "User-Agent": "WhisperFlow"
                    }
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    status_code = getattr(resp, "status", getattr(resp, "code", 200))
                    resp.read()
                latency = int((time.perf_counter() - t0) * 1000.0)
                success = True
                message = f"✓ Connected ({latency}ms latency)"
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    message = "Authentication Failed (401)"
                elif e.code == 429:
                    message = "Rate Limit Exceeded (429)"
                else:
                    message = f"HTTP Error ({e.code})"
            except urllib.error.URLError as e:
                message = "Offline / Network Timeout"
            except Exception as e:
                message = f"Connection Failed: {e}"

            self._api_test_result_signal.emit(success, message)

        threading.Thread(target=_worker, daemon=True).start()

    @Slot(bool, str)
    def _on_api_test_result(self, success: bool, message: str):
        self.test_conn_btn.setEnabled(True)
        self.conn_status_lbl.setText(message)
        if success:
            self.conn_status_lbl.setStyleSheet("color: #34d399; font-weight: bold; font-size: 12px;")
        else:
            self.conn_status_lbl.setStyleSheet("color: #f87171; font-weight: bold; font-size: 12px;")

    def reject(self):
        self._stop_audio_vu_test()
        super().reject()

    def close(self):
        ret = super().close()
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.processEvents()
        return ret

    def closeEvent(self, event):
        self._stop_audio_vu_test()
        super().closeEvent(event)

    def _save_and_accept(self):
        self._stop_audio_vu_test()
        # General
        self.config["engine_mode"] = getattr(self, "engine_mode", self.config.get("engine_mode", "groq"))
        self.config["model_name"] = self.model_combo.currentData()
        self.config["input_device_index"] = self.device_combo.currentData()
        self.config["auto_show_on_textbox"] = self.auto_show_check.isChecked()
        self.config["groq_api_key"] = self.groq_key_input.text().strip()
        if self.whisper_engine:
            self.whisper_engine.groq_api_key = self.config["groq_api_key"]
            self.whisper_engine.engine_mode = self.config["engine_mode"]

        # Voice & Styles
        self.profile["active_style"] = self.profile_mgr.get_active_style()
        self.profile["app_aware_enabled"] = self.app_aware_check.isChecked()
        self.profile["custom_persona_prompt"] = self.persona_edit.toPlainText().strip()
        self.profile_mgr.save_profile()

        self.accept()
