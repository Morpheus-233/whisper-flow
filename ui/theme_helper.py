import sys
import ctypes
from ctypes import c_int, byref, sizeof
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

def apply_dark_window_attributes(widget):
    """
    1. Sets the dialog's palette background to dark #0f172a so the Win32 window
       brush is initialized dark from the first pixel painted (eliminating white flash).
    2. Enables Windows 10/11 DWM immersive dark mode for native dark title bar.
    """
    pal = widget.palette()
    dark_bg = QColor("#0f172a")
    dark_base = QColor("#1e293b")
    text_color = QColor("#f8fafc")

    pal.setColor(QPalette.ColorRole.Window, dark_bg)
    pal.setColor(QPalette.ColorRole.Base, dark_base)
    pal.setColor(QPalette.ColorRole.WindowText, text_color)
    pal.setColor(QPalette.ColorRole.Text, text_color)
    pal.setColor(QPalette.ColorRole.Button, dark_base)
    pal.setColor(QPalette.ColorRole.ButtonText, text_color)

    widget.setPalette(pal)
    widget.setAutoFillBackground(True)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    if sys.platform == "win32":
        try:
            hwnd = int(widget.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            val = c_int(1)
            hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(val), sizeof(val)
            )
            if hr != 0:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 19, byref(val), sizeof(val)
                )
        except Exception:
            pass
