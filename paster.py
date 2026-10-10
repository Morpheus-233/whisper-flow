import time
import ctypes
from ctypes import wintypes
import pyperclip

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12       # Alt key
VK_V = 0x56
VK_LWIN = 0x5B
VK_RWIN = 0x5C

SW_SHOW = 5
KEYEVENTF_KEYUP = 0x0002

# Terminal classes that require Ctrl+Shift+V to paste from clipboard
TERMINAL_SHIFT_PASTE_CLASSES = (
    "org.wezfurlong.wezterm",        # WezTerm default paste is Ctrl+Shift+V
    "alacritty",                     # Alacritty default paste is Ctrl+Shift+V
    "mintty",                        # Git Bash
    "ghostty",                       # Ghostty default paste is Ctrl+Shift+V
    "com.mitchellh.ghostty",
    "kitty",                         # Kitty
)

class Paster:
    def __init__(self):
        pass

    def release_modifiers(self):
        """Non-blocking release of modifier keys with minimal latency."""
        # Quick check if physical keys are down
        alt_down = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
        ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
        shift_down = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)

        if alt_down or ctrl_down or shift_down:
            time.sleep(0.02)

        # Send instant key-up flags
        for vk in [VK_MENU, VK_CONTROL, VK_SHIFT, VK_LWIN, VK_RWIN]:
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    def set_clipboard(self, text):
        """Sets text to Windows clipboard."""
        try:
            pyperclip.copy(text)
        except Exception as e:
            print(f"Clipboard copy error: {e}")

    def send_ctrl_v(self):
        """Simulates native Windows Ctrl+V with zero lag."""
        self.release_modifiers()
        time.sleep(0.015)

        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.015)
        user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    def send_ctrl_shift_v(self):
        """Simulates native Windows Ctrl+Shift+V for terminal emulators like WezTerm."""
        self.release_modifiers()
        time.sleep(0.015)

        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_SHIFT, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.015)
        user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    def instant_paste(self, text, target_hwnd=None, widget_hwnd=None, on_pasted_callback=None):
        """
        Instant, latency-free text injection into the active text box.
        """
        self.set_clipboard(text)

        current_fg = user32.GetForegroundWindow()

        chosen_hwnd = None
        if current_fg and current_fg != widget_hwnd and user32.IsWindow(current_fg):
            chosen_hwnd = current_fg
        elif target_hwnd and user32.IsWindow(target_hwnd):
            chosen_hwnd = target_hwnd

        # Restore window focus if needed
        if chosen_hwnd and user32.IsWindow(chosen_hwnd) and current_fg != chosen_hwnd:
            try:
                current_tid = kernel32.GetCurrentThreadId()
                target_tid = user32.GetWindowThreadProcessId(chosen_hwnd, None)

                if current_tid != target_tid:
                    user32.AttachThreadInput(current_tid, target_tid, True)
                    user32.ShowWindow(chosen_hwnd, SW_SHOW)
                    user32.SetForegroundWindow(chosen_hwnd)
                    user32.BringWindowToTop(chosen_hwnd)
                    user32.SetFocus(chosen_hwnd)
                    user32.AttachThreadInput(current_tid, target_tid, False)
                else:
                    user32.SetForegroundWindow(chosen_hwnd)
            except Exception as e:
                print(f"Focus restore note: {e}")

        # Check if target window requires Ctrl+Shift+V (e.g. WezTerm, Alacritty)
        is_terminal_shift = False
        if chosen_hwnd and user32.IsWindow(chosen_hwnd):
            buf = (ctypes.c_wchar * 256)()
            user32.GetClassNameW(chosen_hwnd, buf, 256)
            target_cls = buf.value.lower()
            if any(term in target_cls for term in TERMINAL_SHIFT_PASTE_CLASSES):
                is_terminal_shift = True

        time.sleep(0.02)
        if is_terminal_shift:
            self.send_ctrl_shift_v()
        else:
            self.send_ctrl_v()

        if on_pasted_callback:
            on_pasted_callback()
