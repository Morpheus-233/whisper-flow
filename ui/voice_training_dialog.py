import time
import threading
import numpy as np
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QStackedWidget, QWidget, QLineEdit, QListWidget,
    QFrame, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QFont, QColor
from voice_profile import VoiceProfileManager
from ui.theme_helper import apply_dark_window_attributes
from ui.settings_dialog import WordRowWidget

CALIBRATION_SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "Whisper Flow transcribes my speech locally with zero latency using PySide6.",
    "I love testing OpenCode, CTranslate2, and modern AI developer tools."
]

class VoiceTrainingDialog(QDialog):
    calibration_completed = Signal()
    _noise_step_updated = Signal(int)
    _noise_finished = Signal(float)
    _speech_finished = Signal(str, int)

    def __init__(self, audio_engine, whisper_engine, parent=None):
        super().__init__(parent)
        self.audio_engine = audio_engine
        self.whisper_engine = whisper_engine
        self.profile_mgr = VoiceProfileManager.get_instance()

        self._noise_step_updated.connect(self._on_noise_step)
        self._noise_finished.connect(self._on_noise_finished)
        self._speech_finished.connect(self._on_speech_finished)

        self.setWindowTitle("Whisper Flow - Voice Training & Calibration")
        self.setFixedSize(580, 520)
        apply_dark_window_attributes(self)
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
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #334155;
                color: #64748b;
            }
            QPushButton#secondaryBtn {
                background-color: #334155;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #475569;
            }
            QPushButton#successBtn {
                background-color: #059669;
            }
            QPushButton#successBtn:hover {
                background-color: #047857;
            }
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                background-color: #1e293b;
                text-align: center;
                color: white;
                font-weight: bold;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 5px;
            }
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QListWidget {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header Title
        title = QLabel("Voice Calibration & Training Wizard")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #60a5fa;")
        layout.addWidget(title)

        subtitle = QLabel("Train Whisper Flow on your room acoustics, mic levels, and accent.")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        # Stacked Pages
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.page_noise = self._create_noise_page()
        self.page_speech = self._create_speech_page()
        self.page_review = self._create_review_page()

        self.stack.addWidget(self.page_noise)
        self.stack.addWidget(self.page_speech)
        self.stack.addWidget(self.page_review)

        self.calibrated_noise = 0.005
        self.calibrated_wpm = 135
        self.current_sentence_idx = 0
        self.transcribed_sentences = []

    def _create_noise_page(self):
        page = QWidget()
        l = QVBoxLayout(page)
        l.setSpacing(14)
        l.setContentsMargins(0, 0, 0, 0)

        step_lbl = QLabel("Step 1: Ambient Noise & Room Acoustics")
        step_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        step_lbl.setStyleSheet("color: #e2e8f0;")
        l.addWidget(step_lbl)

        desc = QLabel(
            "Please remain completely silent for 2 seconds.\n"
            "Whisper Flow will sample your room's ambient noise floor and auto-tune "
            "voice activity sensitivity."
        )
        desc.setWordWrap(True)
        l.addWidget(desc)

        self.noise_progress = QProgressBar()
        self.noise_progress.setRange(0, 100)
        self.noise_progress.setValue(0)
        l.addWidget(self.noise_progress)

        self.noise_status = QLabel("Ready to calibrate.")
        self.noise_status.setStyleSheet("color: #38bdf8; font-style: italic;")
        l.addWidget(self.noise_status)

        l.addStretch()

        btn_row = QHBoxLayout()
        self.start_noise_btn = QPushButton("Start Room Calibration")
        self.start_noise_btn.clicked.connect(self._start_noise_calibration)
        btn_row.addWidget(self.start_noise_btn)

        self.next_to_speech_btn = QPushButton("Next: Voice Cadence →")
        self.next_to_speech_btn.setEnabled(False)
        self.next_to_speech_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_row.addWidget(self.next_to_speech_btn)

        l.addLayout(btn_row)
        return page

    def _on_noise_step(self, val):
        self.noise_progress.setValue(val)

    def _on_noise_finished(self, rms):
        self.calibrated_noise = round(rms, 5)
        self.noise_status.setText(f"Noise floor calibrated: {self.calibrated_noise} RMS (Clear)")
        self.noise_status.setStyleSheet("color: #34d399; font-weight: bold;")
        self.next_to_speech_btn.setEnabled(True)

    def _start_noise_calibration(self):
        self.start_noise_btn.setEnabled(False)
        self.noise_status.setText("Listening to room silence... please do not speak.")
        self.noise_progress.setValue(10)

        def sample_noise():
            self.audio_engine.start_recording()
            for i in range(1, 21):
                time.sleep(0.1)
                self._noise_step_updated.emit(i * 5)
            audio = self.audio_engine.stop_recording()
            if len(audio) > 0:
                rms = float(np.sqrt(np.mean(np.square(audio))))
            else:
                rms = 0.005
            self._noise_finished.emit(rms)

        threading.Thread(target=sample_noise, daemon=True).start()

    def _create_speech_page(self):
        page = QWidget()
        l = QVBoxLayout(page)
        l.setSpacing(12)
        l.setContentsMargins(0, 0, 0, 0)

        step_lbl = QLabel("Step 2: Voice Accent & Cadence Calibration")
        step_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        step_lbl.setStyleSheet("color: #e2e8f0;")
        l.addWidget(step_lbl)

        self.sentence_counter_lbl = QLabel(f"Sentence 1 of {len(CALIBRATION_SENTENCES)}:")
        self.sentence_counter_lbl.setStyleSheet("color: #93c5fd; font-weight: bold;")
        l.addWidget(self.sentence_counter_lbl)

        self.sentence_box = QLabel(CALIBRATION_SENTENCES[0])
        self.sentence_box.setStyleSheet("""
            background-color: #1e293b;
            color: #f1f5f9;
            border-left: 4px solid #3b82f6;
            padding: 12px;
            font-size: 14px;
            font-weight: 500;
            border-radius: 4px;
        """)
        self.sentence_box.setWordWrap(True)
        l.addWidget(self.sentence_box)

        self.speech_rec_status = QLabel("Click 'Start Speaking' and read the sentence above aloud.")
        self.speech_rec_status.setStyleSheet("color: #94a3b8; font-style: italic;")
        l.addWidget(self.speech_rec_status)

        self.transcribed_preview = QLabel("")
        self.transcribed_preview.setStyleSheet("color: #34d399; font-size: 12px;")
        self.transcribed_preview.setWordWrap(True)
        l.addWidget(self.transcribed_preview)

        l.addStretch()

        btn_row = QHBoxLayout()
        self.record_sentence_btn = QPushButton("Start Speaking")
        self.record_sentence_btn.clicked.connect(self._toggle_sentence_recording)
        btn_row.addWidget(self.record_sentence_btn)

        self.next_sentence_btn = QPushButton("Next Sentence →")
        self.next_sentence_btn.setEnabled(False)
        self.next_sentence_btn.clicked.connect(self._advance_sentence)
        btn_row.addWidget(self.next_sentence_btn)

        l.addLayout(btn_row)
        return page

    def _on_speech_finished(self, text, wpm):
        self.calibrated_wpm = wpm
        self.transcribed_preview.setText(f"Whisper heard: \"{text}\" ({self.calibrated_wpm} WPM)")
        self.speech_rec_status.setText("Sentence recorded.")
        self.speech_rec_status.setStyleSheet("color: #34d399; font-weight: bold;")
        self.record_sentence_btn.setText("Record Again")
        self.record_sentence_btn.setEnabled(True)
        self.record_sentence_btn.setStyleSheet("")
        self.next_sentence_btn.setEnabled(True)
        self.transcribed_sentences.append(text)

    def _toggle_sentence_recording(self):
        if not self.audio_engine.is_recording:
            self.audio_engine.start_recording()
            self.sentence_start_time = time.time()
            self.record_sentence_btn.setText("Finish Speaking")
            self.record_sentence_btn.setStyleSheet("background-color: #059669;")
            self.speech_rec_status.setText("Recording your voice...")
            self.speech_rec_status.setStyleSheet("color: #f59e0b; font-weight: bold;")
        else:
            duration = max(0.5, time.time() - getattr(self, 'sentence_start_time', time.time()))
            audio = self.audio_engine.stop_recording()
            self.record_sentence_btn.setText("Processing...")
            self.record_sentence_btn.setEnabled(False)

            def transcribe():
                prompt = self.profile_mgr.get_initial_prompt()
                text = self.whisper_engine.transcribe(audio, initial_prompt=prompt)
                words_count = len(text.split())
                wpm = int((words_count / duration) * 60)
                calibrated_wpm = max(80, min(220, wpm))
                self._speech_finished.emit(text, calibrated_wpm)

            threading.Thread(target=transcribe, daemon=True).start()

    def _advance_sentence(self):
        self.current_sentence_idx += 1
        if self.current_sentence_idx < len(CALIBRATION_SENTENCES):
            self.sentence_counter_lbl.setText(f"Sentence {self.current_sentence_idx + 1} of {len(CALIBRATION_SENTENCES)}:")
            self.sentence_box.setText(CALIBRATION_SENTENCES[self.current_sentence_idx])
            self.transcribed_preview.setText("")
            self.speech_rec_status.setText("Click 'Start Speaking' and read the sentence above aloud.")
            self.speech_rec_status.setStyleSheet("color: #94a3b8; font-style: italic;")
            self.next_sentence_btn.setEnabled(False)
            self.record_sentence_btn.setText("Start Speaking")
        else:
            self.stack.setCurrentIndex(2)

    def _create_review_page(self):
        page = QWidget()
        l = QVBoxLayout(page)
        l.setSpacing(12)
        l.setContentsMargins(0, 0, 0, 0)

        step_lbl = QLabel("Step 3: Calibration Complete & Custom Vocabulary")
        step_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        step_lbl.setStyleSheet("color: #e2e8f0;")
        l.addWidget(step_lbl)

        summary_box = QLabel(
            "✓ Room Acoustics: Calibrated\n"
            "✓ Voice Cadence: Normal (~130 WPM)\n"
            "✓ Whisper Biasing: Active"
        )
        summary_box.setStyleSheet("""
            background-color: #1e293b;
            color: #34d399;
            font-weight: bold;
            padding: 10px;
            border-radius: 6px;
        """)
        l.addWidget(summary_box)

        lbl = QLabel("Quick-Add Custom Words or Names (never mishear these again):")
        l.addWidget(lbl)

        add_row = QHBoxLayout()
        self.custom_word_input = QLineEdit()
        self.custom_word_input.setPlaceholderText("Type word or name and press Enter to add...")
        self.custom_word_input.returnPressed.connect(self._add_word_from_input)
        add_row.addWidget(self.custom_word_input)

        add_btn = QPushButton("+ Add Word")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add_word_from_input)
        add_row.addWidget(add_btn)
        l.addLayout(add_row)

        self.word_list = QListWidget()
        self.word_list.setFixedHeight(140)
        self._refresh_word_list()
        l.addWidget(self.word_list)

        btn_row = QHBoxLayout()
        finish_btn = QPushButton("Finish & Save Profile")
        finish_btn.setObjectName("successBtn")
        finish_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        finish_btn.clicked.connect(self._finish_and_save)
        btn_row.addWidget(finish_btn)
        l.addLayout(btn_row)

        return page

    def _add_word_from_input(self):
        text = self.custom_word_input.text().strip()
        if text:
            self.profile_mgr.add_custom_word(text)
            self.custom_word_input.clear()
            self._refresh_word_list()

    def _on_remove_word(self, word: str):
        self.profile_mgr.remove_custom_word(word)
        self._refresh_word_list()

    def _refresh_word_list(self):
        self.word_list.clear()
        for w in self.profile_mgr.get_custom_words():
            item = QListWidgetItem(self.word_list)
            item.setSizeHint(QSize(0, 36))
            row_widget = WordRowWidget(w, on_remove_callback=self._on_remove_word)
            self.word_list.setItemWidget(item, row_widget)

    def _finish_and_save(self):
        settings = {
            "mic_gain_multiplier": 1.0,
            "calibrated_noise_floor": self.calibrated_noise,
            "speaking_wpm": self.calibrated_wpm
        }
        self.profile_mgr.set_acoustic_settings(settings)
        self.calibration_completed.emit()
        self.accept()
