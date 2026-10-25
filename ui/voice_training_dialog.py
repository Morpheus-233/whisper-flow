import time
import threading
import numpy as np
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QStackedWidget, QWidget, QLineEdit, QListWidget,
    QFrame, QListWidgetItem, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QFont, QColor
from voice_profile import VoiceProfileManager
from ui.theme_helper import apply_dark_window_attributes
from ui.settings_dialog import WordRowWidget, ReplacementRowWidget
from style_engine import FastDevanagariRomanizer
from calibration_engine import load_calibration_dataset, compute_diff, auto_register_misheard_pairs

CALIBRATION_DATASET = load_calibration_dataset()
CALIBRATION_SENTENCES = [s["text"] for s in CALIBRATION_DATASET]


class PhoneticPairChip(QWidget):
    """
    Candidate confirmation chip for misheard phonetic pairs during voice calibration.
    Supports 1-click permanent registration to VoiceProfileManager or 1-click dismissal.
    """
    def __init__(self, heard: str, target: str, on_confirm=None, on_dismiss=None, parent=None):
        super().__init__(parent)
        self.heard = heard
        self.target = target
        self.on_confirm = on_confirm
        self.on_dismiss = on_dismiss

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 8, 4)
        layout.setSpacing(8)

        self.setStyleSheet("""
            PhoneticPairChip {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
            }
        """)

        self.label = QLabel(f"'{heard}' → '{target}'")
        self.label.setStyleSheet("""
            color: #f1f5f9;
            font-size: 12px;
            font-weight: 500;
        """)
        layout.addWidget(self.label)

        self.btn_confirm = QPushButton("+ Remember")
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: #059669;
                color: #ecfdf5;
            }
        """)
        self.btn_confirm.clicked.connect(self._handle_confirm)
        layout.addWidget(self.btn_confirm)

        self.btn_dismiss = QPushButton("✕")
        self.btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dismiss.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: #ffffff;
                border-color: #dc2626;
            }
        """)
        self.btn_dismiss.clicked.connect(self._handle_dismiss)
        layout.addWidget(self.btn_dismiss)

    def _handle_confirm(self):
        try:
            VoiceProfileManager.get_instance().add_replacement(self.heard, self.target)
        except Exception:
            pass
        if callable(self.on_confirm):
            self.on_confirm(self.heard, self.target)
        self.btn_confirm.setText("✓ Remembered")
        self.btn_confirm.setEnabled(False)

    def _handle_dismiss(self):
        if callable(self.on_dismiss):
            self.on_dismiss(self.heard, self.target)
        self.hide()


class VoiceTrainingDialog(QDialog):
    calibration_completed = Signal()
    _noise_step_updated = Signal(int)
    _noise_finished = Signal(float)
    _speech_finished = Signal(object)

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

        self.calibrated_noise = 0.005
        self.calibrated_wpm = 135
        self.current_sentence_idx = 0
        self.transcribed_sentences = []
        self.auto_registered_count = 0
        self.calibration_dataset = CALIBRATION_DATASET
        self.filtered_dataset = list(self.calibration_dataset)

        # Stacked Pages
        self.stack = QStackedWidget()
        self.stack.currentChanged.connect(self._on_page_changed)
        layout.addWidget(self.stack)

        self.page_noise = self._create_noise_page()
        self.page_speech = self._create_speech_page()
        self.page_review = self._create_review_page()

        self.stack.addWidget(self.page_noise)
        self.stack.addWidget(self.page_speech)
        self.stack.addWidget(self.page_review)

    def _on_page_changed(self, idx):
        if idx == 2:
            self._update_review_summary()
            self._refresh_word_list()
            self._refresh_replacements_list()

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
        l.setSpacing(10)
        l.setContentsMargins(0, 0, 0, 0)

        step_lbl = QLabel("Step 2: Bilingual Voice & Accent Calibration")
        step_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        step_lbl.setStyleSheet("color: #e2e8f0;")
        l.addWidget(step_lbl)

        # Filter row: category selector + counter badge
        filter_row = QHBoxLayout()
        filter_lbl = QLabel("Filter:")
        filter_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        filter_row.addWidget(filter_lbl)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["All Sentences (100)", "English (50)", "Hindi / Hinglish (50)"])
        self.category_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #2563eb;
            }
        """)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        filter_row.addWidget(self.category_combo)

        filter_row.addStretch()

        self.sentence_counter_lbl = QLabel("")
        self.sentence_counter_lbl.setStyleSheet("color: #93c5fd; font-weight: bold; font-size: 12px;")
        filter_row.addWidget(self.sentence_counter_lbl)

        l.addLayout(filter_row)

        self.sentence_box = QLabel("")
        self.sentence_box.setStyleSheet("""
            background-color: #1e293b;
            color: #f1f5f9;
            border-left: 4px solid #3b82f6;
            padding: 12px;
            font-size: 14px;
            font-weight: 500;
            border-radius: 4px;
            min-height: 48px;
        """)
        self.sentence_box.setWordWrap(True)
        l.addWidget(self.sentence_box)

        self.keywords_lbl = QLabel("")
        self.keywords_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        l.addWidget(self.keywords_lbl)

        self.speech_rec_status = QLabel("Click 'Start Speaking' and read the sentence above aloud.")
        self.speech_rec_status.setStyleSheet("color: #94a3b8; font-style: italic;")
        l.addWidget(self.speech_rec_status)

        self.transcribed_preview = QLabel("")
        self.transcribed_preview.setStyleSheet("color: #34d399; font-size: 12px;")
        self.transcribed_preview.setWordWrap(True)
        l.addWidget(self.transcribed_preview)

        self.diff_status = QLabel("")
        self.diff_status.setStyleSheet("color: #38bdf8; font-size: 11px;")
        self.diff_status.setWordWrap(True)
        l.addWidget(self.diff_status)

        # Chips container for candidate confirmation chips
        self.chips_container = QWidget()
        self.chips_layout = QHBoxLayout(self.chips_container)
        self.chips_layout.setContentsMargins(0, 4, 0, 4)
        self.chips_layout.setSpacing(8)
        self.chips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        l.addWidget(self.chips_container)

        l.addStretch()

        # Nav & Record Buttons Row
        btn_row = QHBoxLayout()
        self.prev_sentence_btn = QPushButton("← Prev")
        self.prev_sentence_btn.setObjectName("secondaryBtn")
        self.prev_sentence_btn.setEnabled(False)
        self.prev_sentence_btn.clicked.connect(self._prev_sentence)
        btn_row.addWidget(self.prev_sentence_btn)

        self.record_sentence_btn = QPushButton("Start Speaking")
        self.record_sentence_btn.clicked.connect(self._toggle_sentence_recording)
        btn_row.addWidget(self.record_sentence_btn)

        self.next_sentence_btn = QPushButton("Next Sentence →")
        self.next_sentence_btn.clicked.connect(self._advance_sentence)
        btn_row.addWidget(self.next_sentence_btn)

        self.review_jump_btn = QPushButton("Review & Save →")
        self.review_jump_btn.setObjectName("secondaryBtn")
        self.review_jump_btn.clicked.connect(self._jump_to_review)
        btn_row.addWidget(self.review_jump_btn)

        l.addLayout(btn_row)

        self._update_sentence_view()
        return page

    def _clear_chips(self):
        if hasattr(self, "chips_layout") and self.chips_layout is not None:
            while self.chips_layout.count():
                item = self.chips_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()

    def _on_category_changed(self, idx):
        if idx == 1:
            self.filtered_dataset = [s for s in self.calibration_dataset if s.get("category") == "english"]
        elif idx == 2:
            self.filtered_dataset = [s for s in self.calibration_dataset if s.get("category") == "hindi_hinglish"]
        else:
            self.filtered_dataset = list(self.calibration_dataset)
        self.current_sentence_idx = 0
        self._update_sentence_view()

    def _update_keywords_display(self):
        if self.filtered_dataset and self.current_sentence_idx < len(self.filtered_dataset):
            kws = self.filtered_dataset[self.current_sentence_idx].get("phonetic_keywords", [])
            if kws:
                self.keywords_lbl.setText("Phonetic targets: " + ", ".join(kws))
                return
        self.keywords_lbl.setText("")

    def _update_sentence_view(self):
        if not self.filtered_dataset:
            return
        self._clear_chips()
        self.current_sentence_idx = max(0, min(self.current_sentence_idx, len(self.filtered_dataset) - 1))
        item = self.filtered_dataset[self.current_sentence_idx]
        cat = item.get("category", "")
        badge = "[English]" if cat == "english" else "[Hindi/Hinglish]"
        self.sentence_counter_lbl.setText(f"Sentence {self.current_sentence_idx + 1} of {len(self.filtered_dataset)} {badge}:")
        self.sentence_box.setText(item.get("text", ""))
        self._update_keywords_display()
        self.transcribed_preview.setText("")
        self.diff_status.setText("")
        self.speech_rec_status.setText("Click 'Start Speaking' and read the sentence above aloud.")
        self.speech_rec_status.setStyleSheet("color: #94a3b8; font-style: italic;")
        self.prev_sentence_btn.setEnabled(self.current_sentence_idx > 0)
        self.next_sentence_btn.setEnabled(True)
        self.record_sentence_btn.setText("Start Speaking")
        self.record_sentence_btn.setStyleSheet("")

    def _prev_sentence(self):
        if self.current_sentence_idx > 0:
            self.current_sentence_idx -= 1
            self._update_sentence_view()

    def _advance_sentence(self):
        if self.current_sentence_idx + 1 < len(self.filtered_dataset):
            self.current_sentence_idx += 1
            self._update_sentence_view()
        else:
            self._jump_to_review()

    def _jump_to_review(self):
        self._update_review_summary()
        self._refresh_word_list()
        self._refresh_replacements_list()
        self.stack.setCurrentIndex(2)

    def _on_speech_finished(self, data):
        if isinstance(data, dict):
            text = data.get("text", "")
            wpm = data.get("wpm", 135)
            diff_res = data.get("diff_res", {})
            newly_added = data.get("newly_added", 0)
        else:
            text = str(data)
            wpm = 135
            target_item = self.filtered_dataset[self.current_sentence_idx] if self.filtered_dataset else {}
            target_text = target_item.get("text", "")
            keywords = target_item.get("phonetic_keywords", [])
            diff_res = compute_diff(target_text, text, keywords)
            newly_added = 0

        self.calibrated_wpm = wpm
        accuracy = diff_res.get("accuracy", 100.0)
        misheard = diff_res.get("misheard_pairs", [])

        self.transcribed_preview.setText(f'Whisper heard: "{text}"  |  Accuracy: {accuracy:.1f}% ({self.calibrated_wpm} WPM)')

        # Clear old chips
        self._clear_chips()

        if misheard:
            pairs_str = ", ".join(f"'{p['heard']}' -> '{p['target']}'" for p in misheard)
            if newly_added > 0:
                self.diff_status.setText(f"Auto-registered {newly_added} phonetic correction(s): {pairs_str}")
                self.diff_status.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold;")
                self.auto_registered_count += newly_added
            else:
                self.diff_status.setText("Candidate phonetic correction(s) detected — click '+ Remember' to save:")
                self.diff_status.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold;")

            for p in misheard:
                h = p.get("heard", "").strip()
                t = p.get("target", "").strip()
                if not h or not t:
                    continue

                def make_callbacks(heard_word, target_word):
                    def on_confirm(hw, tw):
                        self.profile_mgr.add_replacement(hw, tw)
                        self.auto_registered_count += 1
                        self.diff_status.setText(f"Remembered phonetic mapping: '{hw}' → '{tw}'")
                        self.diff_status.setStyleSheet("color: #34d399; font-size: 11px; font-weight: bold;")
                        self._update_review_summary()

                    def on_dismiss(hw, tw):
                        pass

                    return on_confirm, on_dismiss

                on_conf, on_dism = make_callbacks(h, t)
                chip = PhoneticPairChip(h, t, on_confirm=on_conf, on_dismiss=on_dism)
                if self.profile_mgr.get_replacements().get(h.lower()) == t:
                    chip.btn_confirm.setText("✓ Remembered")
                    chip.btn_confirm.setEnabled(False)
                self.chips_layout.addWidget(chip)

        elif accuracy >= 95.0:
            self.diff_status.setText("Excellent pronunciation! Clean match with target.")
            self.diff_status.setStyleSheet("color: #34d399; font-size: 11px; font-weight: bold;")
        else:
            self.diff_status.setText("")

        self.speech_rec_status.setText("Sentence recorded & calibrated.")
        self.speech_rec_status.setStyleSheet("color: #34d399; font-weight: bold;")
        self.record_sentence_btn.setText("Record Again")
        self.record_sentence_btn.setEnabled(True)
        self.record_sentence_btn.setStyleSheet("")
        self.next_sentence_btn.setEnabled(True)
        self.prev_sentence_btn.setEnabled(self.current_sentence_idx > 0)
        self.category_combo.setEnabled(True)
        self.transcribed_sentences.append(text)

    def _toggle_sentence_recording(self):
        if not self.audio_engine.is_recording:
            self.audio_engine.start_recording()
            self.sentence_start_time = time.time()
            self.record_sentence_btn.setText("Finish Speaking")
            self.record_sentence_btn.setStyleSheet("background-color: #059669;")
            self.speech_rec_status.setText("Recording your voice...")
            self.speech_rec_status.setStyleSheet("color: #f59e0b; font-weight: bold;")
            self.next_sentence_btn.setEnabled(False)
            self.prev_sentence_btn.setEnabled(False)
            self.category_combo.setEnabled(False)
        else:
            duration = max(0.5, time.time() - getattr(self, 'sentence_start_time', time.time()))
            audio = self.audio_engine.stop_recording()
            self.record_sentence_btn.setText("Processing...")
            self.record_sentence_btn.setEnabled(False)
            self.next_sentence_btn.setEnabled(False)
            self.prev_sentence_btn.setEnabled(False)
            self.category_combo.setEnabled(False)

            # Snapshot target_item before launching background transcription thread
            target_item = dict(self.filtered_dataset[self.current_sentence_idx]) if self.filtered_dataset else {}

            def transcribe():
                prompt = self.profile_mgr.get_initial_prompt()
                text = self.whisper_engine.transcribe(audio, initial_prompt=prompt)

                if target_item.get("category") == "hindi_hinglish" and FastDevanagariRomanizer.has_devanagari(text):
                    text = FastDevanagariRomanizer.romanize(text)

                words_count = len(text.split())
                wpm = int((words_count / duration) * 60)
                calibrated_wpm = max(80, min(220, wpm))

                target_text = target_item.get("text", "")
                keywords = target_item.get("phonetic_keywords", [])

                diff_res = compute_diff(target_text, text, keywords)

                payload = {
                    "text": text,
                    "wpm": calibrated_wpm,
                    "diff_res": diff_res,
                    "newly_added": 0
                }
                self._speech_finished.emit(payload)

            threading.Thread(target=transcribe, daemon=True).start()

    def _update_review_summary(self):
        summary_text = (
            f"✓ Room Acoustics: Calibrated ({self.calibrated_noise} RMS)\n"
            f"✓ Voice Cadence: Normal (~{self.calibrated_wpm} WPM)\n"
            f"✓ Sentences Calibrated: {len(self.transcribed_sentences)}\n"
            f"✓ Phonetic Mappings Registered: {len(self.profile_mgr.get_replacements())}\n"
            f"✓ Whisper Biasing: Active ({len(self.profile_mgr.get_custom_words())} words)"
        )
        if hasattr(self, "review_summary_box"):
            self.review_summary_box.setText(summary_text)

    def _create_review_page(self):
        page = QWidget()
        l = QVBoxLayout(page)
        l.setSpacing(10)
        l.setContentsMargins(0, 0, 0, 0)

        step_lbl = QLabel("Step 3: Calibration Complete & Custom Vocabulary")
        step_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        step_lbl.setStyleSheet("color: #e2e8f0;")
        l.addWidget(step_lbl)

        self.review_summary_box = QLabel("")
        self._update_review_summary()
        self.review_summary_box.setStyleSheet("""
            background-color: #1e293b;
            color: #34d399;
            font-weight: bold;
            padding: 10px;
            border-radius: 6px;
        """)
        l.addWidget(self.review_summary_box)

        # Side-by-side columns: Custom Words (left) and Calibrated Phonetic Mappings (right)
        lists_row = QHBoxLayout()
        lists_row.setSpacing(12)

        # Left Column: Custom Words
        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        words_hdr = QLabel("Custom Vocabulary:")
        words_hdr.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 12px;")
        left_col.addWidget(words_hdr)

        add_row = QHBoxLayout()
        self.custom_word_input = QLineEdit()
        self.custom_word_input.setPlaceholderText("Add word or name...")
        self.custom_word_input.returnPressed.connect(self._add_word_from_input)
        add_row.addWidget(self.custom_word_input)

        add_btn = QPushButton("+ Add")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("padding: 6px 12px; font-size: 12px;")
        add_btn.clicked.connect(self._add_word_from_input)
        add_row.addWidget(add_btn)
        left_col.addLayout(add_row)

        self.word_list = QListWidget()
        self.word_list.setFixedHeight(135)
        left_col.addWidget(self.word_list)
        lists_row.addLayout(left_col)

        # Right Column: Calibrated Phonetic Mappings
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        reps_hdr = QLabel("Calibrated Phonetic Mappings:")
        reps_hdr.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 12px;")
        right_col.addWidget(reps_hdr)

        reps_sub = QLabel("Heard → Target (1-click removal):")
        reps_sub.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic; min-height: 29px;")
        right_col.addWidget(reps_sub)

        self.replacements_list = QListWidget()
        self.replacements_list.setFixedHeight(135)
        right_col.addWidget(self.replacements_list)
        lists_row.addLayout(right_col)

        l.addLayout(lists_row)

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
            self._update_review_summary()

    def _on_remove_word(self, word: str):
        self.profile_mgr.remove_custom_word(word)
        self._refresh_word_list()
        self._update_review_summary()

    def _refresh_word_list(self):
        self.word_list.clear()
        for w in self.profile_mgr.get_custom_words():
            item = QListWidgetItem(self.word_list)
            item.setSizeHint(QSize(0, 36))
            row_widget = WordRowWidget(w, on_remove_callback=self._on_remove_word)
            self.word_list.setItemWidget(item, row_widget)

    def _refresh_replacements_list(self):
        self.replacements_list.clear()
        for heard, target in self.profile_mgr.get_replacements().items():
            item = QListWidgetItem(self.replacements_list)
            item.setSizeHint(QSize(0, 36))
            row_widget = ReplacementRowWidget(heard, target, on_remove_callback=self._on_remove_replacement)
            self.replacements_list.setItemWidget(item, row_widget)

    def _on_remove_replacement(self, heard: str):
        self.profile_mgr.remove_replacement(heard)
        self._refresh_replacements_list()
        self._update_review_summary()

    def _finish_and_save(self):
        settings = {
            "mic_gain_multiplier": 1.0,
            "calibrated_noise_floor": self.calibrated_noise,
            "speaking_wpm": self.calibrated_wpm
        }
        self.profile_mgr.set_acoustic_settings(settings)
        self.calibration_completed.emit()
        self.accept()
