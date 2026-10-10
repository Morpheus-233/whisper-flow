from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class SettingsDialog(QDialog):
    def __init__(self, config, audio_engine, parent=None):
        super().__init__(parent)
        self.config = config
        self.audio_engine = audio_engine
        self.setWindowTitle("Whisper Flow - Preferences")
        self.setFixedWidth(400)
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
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                margin-top: 18px;
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
            QPushButton#cancelBtn {
                background-color: #334155;
            }
            QPushButton#cancelBtn:hover {
                background-color: #475569;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Whisper Flow Settings")
        title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #60a5fa;")
        layout.addWidget(title_label)

        # 1. Model Selection
        model_group = QGroupBox("Whisper Model")
        model_layout = QVBoxLayout(model_group)
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
        model_layout.addWidget(self.model_combo)
        layout.addWidget(model_group)

        # 2. Audio Input Device
        audio_group = QGroupBox("Microphone Input")
        audio_layout = QVBoxLayout(audio_group)
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

        audio_layout.addWidget(self.device_combo)
        layout.addWidget(audio_group)

        # 3. Behavior Group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(behavior_group)
        from PySide6.QtWidgets import QCheckBox
        self.auto_show_check = QCheckBox("Show widget only when clicking into a text box")
        self.auto_show_check.setStyleSheet("color: #f8fafc; font-size: 13px;")
        self.auto_show_check.setChecked(self.config.get("auto_show_on_textbox", True))
        behavior_layout.addWidget(self.auto_show_check)
        layout.addWidget(behavior_group)

        # 4. Shortcut Info
        info_label = QLabel("Global Shortcut: Ctrl + Shift + Space\nAutomatically pastes directly into your active text box.")
        info_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-style: italic;")
        layout.addWidget(info_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Preferences")
        save_btn.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save_and_accept(self):
        self.config["model_name"] = self.model_combo.currentData()
        self.config["input_device_index"] = self.device_combo.currentData()
        self.config["auto_show_on_textbox"] = self.auto_show_check.isChecked()
        self.accept()
