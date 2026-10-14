import sys
import os
import math
import ctypes
from PySide6.QtCore import Qt, QPoint, QTimer, Signal, QRectF
from PySide6.QtWidgets import QWidget, QMenu, QApplication
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath, QLinearGradient

user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008

WM_SHOW_WHISPER_FLOW = user32.RegisterWindowMessageW("WHISPER_FLOW_SHOW_WIDGET_V3")

WM_NCLBUTTONDOWN = 0x00A1
HTCAPTION = 2

STATE_IDLE = "idle"
STATE_RECORDING = "recording"
STATE_TRANSCRIBING = "transcribing"
STATE_PASTED = "pasted"

# Palette: Custom obsidian glass with violet accents for idle, pastel lilac & plum for active bar
COLOR_BG_LILAC  = QColor("#BEA5BB")    # Soft dusty lilac capsule / cancel button
COLOR_PURPLE_BTN= QColor("#66326B")    # Royal plum checkmark circle
COLOR_DARK_PLUM = QColor("#3E2533")    # Waveform bars & X icon
COLOR_WHITE     = QColor("#FFFFFF")

class FloatingWidget(QWidget):
    toggle_recording_requested = Signal()
    cancel_recording_requested = Signal()
    open_settings_requested = Signal()
    model_changed = Signal(str)
    exit_requested = Signal()
    show_requested_from_external = Signal()

    def __init__(self, config, audio_engine):
        super().__init__()
        self.config = config
        self.audio_engine = audio_engine
        self.current_state = STATE_IDLE

        # Window flags: frameless, always-on-top, tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        # 1. Custom Initial Widget Geometry: Sleek Obsidian Capsule Dock
        self.dock_w = 56
        self.dock_h = 34
        self.dock_radius = 17.0

        # 2. Recording State Geometry: 3-Segment Bar from reference image
        self.btn_size = 38
        self.pill_w = 98
        self.pill_h = 38
        self.gap = 7
        self.rec_w = self.btn_size + self.gap + self.pill_w + self.gap + self.btn_size  # ~188px
        self.rec_h = self.btn_size  # 38px

        self.pad_x = 7
        self.pad_y = 6

        # Start in compact idle dock size
        self.setFixedSize(self.dock_w + self.pad_x * 2, self.dock_h + self.pad_y * 2)

        # Positioning
        screen = QApplication.primaryScreen().geometry()
        init_x = self.config.get("window_x")
        init_y = self.config.get("window_y")
        if init_x is None or init_y is None or not QApplication.screenAt(QPoint(int(init_x), int(init_y))):
            init_x = screen.width() // 2 - (self.width() // 2)
            init_y = screen.height() - self.height() - 90
        self.move(int(init_x), int(init_y))

        self._press_pos = QPoint()
        self._is_potential_drag = False
        self._is_hovered = False

        # Waveform animation
        self.num_bars = 13
        self.audio_bars = [0.2] * self.num_bars
        self.pulse_phase = 0.0
        self.spin_angle = 0

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_animation_tick)
        self.anim_timer.start(33)  # ~30 FPS

        # Ultra-fast auto-reset timer for pasted state (only 280ms quick flash, zero waiting)
        self.reset_timer = QTimer(self)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self._reset_to_idle)

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            try:
                from ctypes import wintypes
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_SHOW_WHISPER_FLOW:
                    self.show_requested_from_external.emit()
                    return True, 0
            except Exception:
                pass
        return super().nativeEvent(event_type, message)

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_no_activate()

    def moveEvent(self, event):
        super().moveEvent(event)
        try:
            if hasattr(self, 'config') and self.config is not None:
                self.config["window_x"] = self.x()
                self.config["window_y"] = self.y()
        except Exception:
            pass

    def _apply_no_activate(self):
        """Prevent window from stealing focus when clicked."""
        try:
            hwnd = int(self.winId())
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOPMOST)
        except Exception as e:
            print(f"Error setting WS_EX_NOACTIVATE: {e}")

    def set_state(self, state, message=None):
        old_state = self.current_state
        self.current_state = state

        # Center-anchored seamless resize between idle dock & recording bar
        if state == STATE_IDLE:
            if old_state != STATE_IDLE:
                cx = self.x() + self.width() // 2
                cy = self.y() + self.height() // 2
                self.setFixedSize(self.dock_w + self.pad_x * 2, self.dock_h + self.pad_y * 2)
                self.move(cx - self.width() // 2, cy - self.height() // 2)
            else:
                self.setFixedSize(self.dock_w + self.pad_x * 2, self.dock_h + self.pad_y * 2)
        else:
            if old_state == STATE_IDLE:
                cx = self.x() + self.width() // 2
                cy = self.y() + self.height() // 2
                self.setFixedSize(self.rec_w + self.pad_x * 2, self.rec_h + self.pad_y * 2)
                self.move(cx - self.width() // 2, cy - self.height() // 2)
            else:
                self.setFixedSize(self.rec_w + self.pad_x * 2, self.rec_h + self.pad_y * 2)

        self._apply_no_activate()

        # Snappy, instant return to idle (280ms flash, no 2-second delay)
        if state == STATE_PASTED:
            self.reset_timer.start(280)

        self.update()

    def _reset_to_idle(self):
        if self.current_state == STATE_PASTED:
            self.set_state(STATE_IDLE)

    def _on_animation_tick(self):
        self.pulse_phase += 0.12
        if self.pulse_phase > 2 * math.pi:
            self.pulse_phase = 0.0

        if self.current_state == STATE_RECORDING:
            vol = self.audio_engine.get_current_volume()
            for i in range(self.num_bars):
                center_dist = abs(i - (self.num_bars - 1) / 2.0) / ((self.num_bars - 1) / 2.0)
                taper = max(0.18, 1.0 - (center_dist * 0.72))
                target = min(1.0, max(0.12, vol * taper * (0.8 + 0.45 * math.sin(self.pulse_phase * 2.5 + i * 0.9))))
                self.audio_bars[i] = 0.55 * self.audio_bars[i] + 0.45 * target
            self.update()
        elif self.current_state == STATE_TRANSCRIBING:
            self.spin_angle = (self.spin_angle + 12) % 360
            self.update()
        elif self.current_state in (STATE_IDLE, STATE_PASTED):
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._is_potential_drag = True
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton) and self._is_potential_drag:
            dist = (event.globalPosition().toPoint() - self._press_pos).manhattanLength()
            if dist > 5:
                self._is_potential_drag = False
                hwnd = int(self.winId())
                user32.ReleaseCapture()
                user32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)
                # Save position
                self.config["window_x"] = self.x()
                self.config["window_y"] = self.y()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_potential_drag:
                self._is_potential_drag = False

                if self.current_state == STATE_IDLE:
                    # Clicking the custom dock starts recording instantly!
                    self.toggle_recording_requested.emit()
                else:
                    # In recording state:
                    click_x = event.position().x() - self.pad_x
                    left_edge = self.btn_size
                    right_edge = self.btn_size + self.gap + self.pill_w

                    if click_x <= left_edge:
                        # [X] button clicked: cancel recording immediately (0ms delay)
                        self.cancel_recording_requested.emit()
                    elif click_x >= right_edge:
                        # [✓] button clicked: finish and paste
                        self.toggle_recording_requested.emit()
                    else:
                        # Center waveform clicked: finish and paste
                        self.toggle_recording_requested.emit()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #12131d;
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #66326b;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 0.1);
                margin: 4px 8px;
            }
        """)

        # Model submenu
        model_menu = menu.addMenu(f"Model: {self.config.get('model_name', 'base.en')}")
        model_menu.setStyleSheet(menu.styleSheet())
        for m in ["small", "base", "base.en", "small.en", "tiny.en"]:
            act = model_menu.addAction(m)
            if m == self.config.get("model_name"):
                act.setIconText("✓")
            act.triggered.connect(lambda checked=False, model=m: self.model_changed.emit(model))

        # Speech Style submenu
        from voice_profile import VoiceProfileManager
        profile_mgr = VoiceProfileManager.get_instance()
        cur_style = profile_mgr.get_active_style()
        style_menu = menu.addMenu(f"Style: {cur_style.capitalize()}")
        style_menu.setStyleSheet(menu.styleSheet())
        styles = [
            ("Professional / Executive", "professional"),
            ("Casual Chat", "casual"),
            ("Developer / Code", "code"),
            ("Raw Cleaned", "raw"),
            ("Custom Persona", "custom")
        ]
        for label, key in styles:
            act = style_menu.addAction(label)
            if key == cur_style:
                act.setIconText("✓")
            act.triggered.connect(lambda checked=False, s=key: profile_mgr.set_active_style(s))

        menu.addSeparator()

        settings_action = menu.addAction("⚙ Preferences & Microphone...")
        settings_action.triggered.connect(self.open_settings_requested.emit)

        menu.addSeparator()

        exit_action = menu.addAction("✕ Quit Whisper Flow")
        exit_action.triggered.connect(self.exit_requested.emit)

        menu.exec(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        y = self.pad_y

        if self.current_state == STATE_IDLE:
            # ─────────────────────────────────────────────────────────────
            # 1. BESPOKE OBSIDIAN CAPSULE DOCK (Clean, High-End Initial Widget)
            # ─────────────────────────────────────────────────────────────
            x = self.pad_x
            dock_rect = QRectF(x, y, self.dock_w, self.dock_h)
            center = dock_rect.center()
            cx, cy = center.x(), center.y()

            # Obsidian glass background with subtle violet gradient
            bg_color = QColor(14, 15, 24, 244)
            dock_path = QPainterPath()
            dock_path.addRoundedRect(dock_rect, self.dock_radius, self.dock_radius)
            painter.fillPath(dock_path, QBrush(bg_color))

            # Specular luminous rim (glows on hover or breathes gently)
            pulse = (math.sin(self.pulse_phase) + 1.0) / 2.0
            border_alpha = int(120 + 80 * pulse) if self._is_hovered else int(65 + 35 * pulse)
            border_pen = QPen(QColor(168, 85, 247, border_alpha), 1.4)
            painter.setPen(border_pen)
            painter.drawPath(dock_path)

            # Minimalist 3-bar voice emblem inside capsule: | | |
            # Center bar is slightly taller, outer bars gently breathe
            bar_w = 2.6
            bar_gap = 4.2
            painter.setPen(Qt.PenStyle.NoPen)

            h_center = 14.0 + 1.5 * math.sin(self.pulse_phase * 2)
            h_outer = 8.5 + 1.0 * math.sin(self.pulse_phase * 2 + 1.0)

            # Center bar (pearl white with violet tint)
            painter.setBrush(QBrush(QColor(245, 243, 255)))
            painter.drawRoundedRect(QRectF(cx - bar_w / 2.0, cy - h_center / 2.0, bar_w, h_center), 1.3, 1.3)

            # Left bar
            painter.setBrush(QBrush(QColor(196, 181, 253)))
            painter.drawRoundedRect(QRectF(cx - bar_gap - bar_w / 2.0, cy - h_outer / 2.0, bar_w, h_outer), 1.3, 1.3)

            # Right bar
            painter.drawRoundedRect(QRectF(cx + bar_gap - bar_w / 2.0, cy - h_outer / 2.0, bar_w, h_outer), 1.3, 1.3)

        else:
            # ─────────────────────────────────────────────────────────────
            # 2. ACTIVE 3-SEGMENT RECORDING BAR (Reference Image Layout)
            # ─────────────────────────────────────────────────────────────
            h = self.btn_size

            # Segment A: Left Circle (Cancel [X])
            x_left = self.pad_x
            left_rect = QRectF(x_left, y, self.btn_size, self.btn_size)
            cx_left = left_rect.center().x()
            cy_left = left_rect.center().y()

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(COLOR_BG_LILAC))
            painter.drawEllipse(left_rect)

            # Draw 'X' icon
            pen_x = QPen(COLOR_DARK_PLUM, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_x)
            d = 4.8
            painter.drawLine(cx_left - d, cy_left - d, cx_left + d, cy_left + d)
            painter.drawLine(cx_left - d, cy_left + d, cx_left + d, cy_left - d)

            # Segment B: Middle Capsule Pill (Live Waveform)
            x_mid = x_left + self.btn_size + self.gap
            mid_rect = QRectF(x_mid, y, self.pill_w, self.pill_h)
            corner_r = self.pill_h / 2.0

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(COLOR_BG_LILAC))
            mid_path = QPainterPath()
            mid_path.addRoundedRect(mid_rect, corner_r, corner_r)
            painter.drawPath(mid_path)

            cx_mid = mid_rect.center().x()
            cy_mid = mid_rect.center().y()

            bar_spacing = 4.6
            wave_bar_w = 2.4
            total_waveform_w = (self.num_bars - 1) * bar_spacing
            start_bx = cx_mid - (total_waveform_w / 2.0)

            pen_wave = QPen(COLOR_DARK_PLUM, wave_bar_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_wave)

            if self.current_state == STATE_RECORDING:
                # Live dynamic voice audio bars
                max_wave_h = 16.0
                for i in range(self.num_bars):
                    bx = start_bx + i * bar_spacing
                    bh = max(2.5, self.audio_bars[i] * max_wave_h)
                    painter.drawLine(bx, cy_mid - bh / 2.0, bx, cy_mid + bh / 2.0)

            elif self.current_state == STATE_TRANSCRIBING:
                # Smooth shimmer pulse
                for i in range(self.num_bars):
                    bx = start_bx + i * bar_spacing
                    phase_offset = math.sin(self.pulse_phase * 3 + i * 0.5)
                    bh = max(2.5, 3.5 + 4.5 * max(0.0, phase_offset))
                    painter.drawLine(bx, cy_mid - bh / 2.0, bx, cy_mid + bh / 2.0)

            else:
                # Resting tapered dots
                static_heights = [2.0, 2.5, 4.0, 7.0, 10.0, 13.0, 15.0, 13.0, 10.0, 7.0, 4.0, 2.5, 2.0]
                for i in range(min(self.num_bars, len(static_heights))):
                    bx = start_bx + i * bar_spacing
                    bh = static_heights[i]
                    painter.drawLine(bx, cy_mid - bh / 2.0, bx, cy_mid + bh / 2.0)

            # Segment C: Right Circle (Done / Checkmark [✓])
            x_right = x_mid + self.pill_w + self.gap
            right_rect = QRectF(x_right, y, self.btn_size, self.btn_size)
            cx_right = right_rect.center().x()
            cy_right = right_rect.center().y()

            right_bg = COLOR_PURPLE_BTN
            if self.current_state == STATE_PASTED:
                right_bg = QColor("#10B981")  # Emerald green flash

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(right_bg))
            painter.drawEllipse(right_rect)

            # Draw Checkmark '✓'
            pen_check = QPen(COLOR_WHITE, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen_check)
            painter.drawLine(cx_right - 4.5, cy_right + 0.5, cx_right - 0.8, cy_right + 4.2)
            painter.drawLine(cx_right - 0.8, cy_right + 4.2, cx_right + 5.5, cy_right - 3.2)
