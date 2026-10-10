import sys
import ctypes
from ctypes import wintypes
import uiautomation as auto

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]

class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]

class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", RECT),
    ]

# Snappy search timeout (120ms) so UIA never blocks or freezes UI responsiveness
auto.SetGlobalSearchTimeout(0.12)

# Known class names of native Win32 edit controls
WIN32_EDIT_CLASSES = (
    "edit",
    "richedit",
    "richedit20w",
    "richedit50w",
    "richedit60w",
    "richeditd2dpt",
    "scintilla",
    "windows.ui.input.inputsite.windowclass",
    "_wwg",             # Microsoft Word document edit pane
    "_wwb",             # Microsoft Word secondary edit pane
    "_wwf",             # Microsoft Word frame
    "paneclassdc",      # Microsoft PowerPoint slide edit canvas
    "mdiclass",         # Microsoft PowerPoint MDI slide area
    "excel7",           # Microsoft Excel cell editor
    "excel6",           # Microsoft Excel formula bar / edit
    "consolewindowclass",
    "cascadia_hosted_window_class",
)

# Window classes that use Chromium CEF / Gecko / Web DOM
CHROMIUM_WINDOW_CLASSES = (
    "chrome_widgetwin",
    "chrome_renderwidgethost",
    "electron",
    "cef",
    "mozillawindowclass",
    "mozilla",
    "sdl_app",          # Steam client / CEF overlay
    "vguipopupwindow",  # Steam popup / CEF windows
    "valve001",
    "steam",
)

# Top-level window classes for Microsoft Office applications
OFFICE_TOP_CLASSES = (
    "opusapp",          # Microsoft Word
    "pptframeclass",    # Microsoft PowerPoint
    "xlmain",           # Microsoft Excel
)

# Terminal and Command Line Interface window classes (interactive CLI sessions like OpenCode)
TERMINAL_WINDOW_CLASSES = (
    "org.wezfurlong.wezterm",        # WezTerm (used for OpenCode)
    "cascadia_hosted_window_class",  # Windows Terminal
    "consolewindowclass",            # Windows Console Host (cmd / powershell)
    "alacritty",                     # Alacritty
    "mintty",                        # Git Bash
    "virtualconsoleclass",           # ConEmu
    "ghostty",                       # Ghostty
    "com.mitchellh.ghostty",
    "kitty",                         # Kitty
    "putty",                         # PuTTY
)

# Constants
WM_GETOBJECT = 0x003D
OBJID_CLIENT = 0xFFFFFFFC
ROLE_SYSTEM_TEXT = 42
STATE_SYSTEM_READONLY = 0x00000040
GWL_STYLE = -16
ES_READONLY = 0x0800

# Optional COM UIAutomation event handler setup for Windows
UIAutomationClient = None
try:
    import comtypes
    from comtypes import COMObject
    import comtypes.client
    UIAutomationClient = comtypes.client.GetModule("UIAutomationCore.dll")
except Exception as _e:
    pass


class FocusDetector:
    def __init__(self, widget_hwnd_getter=None, on_focus_changed=None):
        """
        :param widget_hwnd_getter: Callable returning the HWND of the whisper-flow widget
        :param on_focus_changed: Callable invoked whenever focus changes
        """
        self.widget_hwnd_getter = widget_hwnd_getter
        self.on_focus_changed = on_focus_changed
        self._woken_hwnds = set()
        self._uia_cui = None
        self._focus_handler = None

        if sys.platform == "win32":
            self._init_uia_event_handler()

    def _init_uia_event_handler(self):
        """Registers IUIAutomation::AddFocusChangedEventHandler on Windows."""
        if not UIAutomationClient:
            return
        try:
            detector_ref = self

            class FocusHandler(COMObject):
                _com_interfaces_ = [UIAutomationClient.IUIAutomationFocusChangedEventHandler]

                def HandleFocusChangedEvent(self, sender):
                    try:
                        if detector_ref.on_focus_changed:
                            detector_ref.on_focus_changed()
                    except Exception:
                        pass

            self._uia_cui = comtypes.client.CreateObject(
                UIAutomationClient.CUIAutomation,
                interface=UIAutomationClient.IUIAutomation
            )
            self._focus_handler = FocusHandler()
            self._uia_cui.AddFocusChangedEventHandler(None, self._focus_handler)
            print("[FocusDetector] Registered IUIAutomation::AddFocusChangedEventHandler successfully.")
        except Exception as e:
            print(f"[FocusDetector] Notice: Could not register UIA event handler ({e}), using polling fallback.")
            self._uia_cui = None
            self._focus_handler = None

    def cleanup(self):
        """Unregisters COM event handlers safely."""
        if self._uia_cui and self._focus_handler:
            try:
                self._uia_cui.RemoveFocusChangedEventHandler(self._focus_handler)
            except Exception:
                pass
            self._uia_cui = None
            self._focus_handler = None

    def _wake_chromium_accessibility(self, hwnd: int):
        """
        Enables Chromium accessibility on demand for Spotify, Chrome, Slack, Discord, Steam, etc.
        Sending WM_GETOBJECT with OBJID_CLIENT causes Chromium to activate its accessibility tree.
        """
        try:
            res = wintypes.DWORD()
            user32.SendMessageTimeoutW(hwnd, WM_GETOBJECT, 0, OBJID_CLIENT, 2, 80, ctypes.byref(res))
        except Exception:
            pass

    def get_focused_text_input(self) -> tuple[bool, tuple | None]:
        """
        Authoritative element-level check.
        Returns:
            (is_text_field: bool, bounding_rect: tuple (left, top, right, bottom) or None)

        The widget appears ONLY while an editable text input field has keyboard focus.
        Hides for:
        - buttons, slide canvas, playlist items, player bar, menus, title bars
        - clicking elsewhere in the app
        - desktop or window switch with no focused text field
        - read-only, disabled, or password fields.
        """
        if sys.platform != "win32":
            return False, None

        try:
            fg_hwnd = user32.GetForegroundWindow()
            widget_hwnd = self.widget_hwnd_getter() if self.widget_hwnd_getter else 0

            # Ignore focus events originating from our own widget so clicking it does not hide it
            if fg_hwnd and widget_hwnd and (fg_hwnd == widget_hwnd):
                return True, None

            # Inspect foreground window class if available
            fg_cls = ""
            if fg_hwnd:
                buf = (ctypes.c_wchar * 256)()
                user32.GetClassNameW(fg_hwnd, buf, 256)
                fg_cls = buf.value.lower()

            is_chromium_window = any(c in fg_cls for c in CHROMIUM_WINDOW_CLASSES) if fg_cls else False
            is_office_window = any(o in fg_cls for o in OFFICE_TOP_CLASSES) if fg_cls else False

            # Enable Chromium accessibility for Electron/CEF apps so their text inputs expose UIA data
            if fg_hwnd and is_chromium_window and fg_hwnd not in self._woken_hwnds:
                self._woken_hwnds.add(fg_hwnd)
                self._wake_chromium_accessibility(fg_hwnd)

            # 1. Primary Check: UI Automation focused element (works system-wide across all windows)
            ctrl = auto.GetFocusedControl()
            if ctrl:
                # If focused element is our own widget, maintain visibility
                if widget_hwnd and getattr(ctrl, 'NativeWindowHandle', 0) == widget_hwnd:
                    return True, None

                is_text, rect = self._validate_element(ctrl)
                if is_text:
                    return True, rect

            if not fg_hwnd:
                return False, None

            # 2. Terminal / Command Line Interface Fallback
            # Terminal emulators (WezTerm, Windows Terminal, ConHost, Alacritty, Mintty, etc.)
            # host interactive CLI prompt sessions (OpenCode, shells, REPLs).
            # Modern GPU-accelerated terminals render text directly via GPU swap chains without standard Win32 GUI carets.
            # When a terminal window has keyboard focus, the user is at an interactive CLI prompt.
            if fg_hwnd and any(term in fg_cls for term in TERMINAL_WINDOW_CLASSES):
                rect = RECT()
                user32.GetWindowRect(fg_hwnd, ctypes.byref(rect))
                return True, (rect.left, rect.top, rect.right, rect.bottom)

            # 3. PowerPoint Fallback (PPTFrameClass)
            # PowerPoint shapes, placeholders, and notes pane:
            # Active text editing produces a native Win32 blinking caret in GetGUIThreadInfo.
            # Slide canvas, thumbnail pane, shape outline selection, and ribbon have NO active text caret.
            if "pptframeclass" in fg_cls:
                tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
                if tid:
                    gui = GUITHREADINFO()
                    gui.cbSize = ctypes.sizeof(GUITHREADINFO)
                    if user32.GetGUIThreadInfo(tid, ctypes.byref(gui)):
                        if gui.hwndCaret and user32.IsWindow(gui.hwndCaret):
                            w = gui.rcCaret.right - gui.rcCaret.left
                            h = gui.rcCaret.bottom - gui.rcCaret.top
                            if w > 0 or h > 0:
                                pt = POINT(gui.rcCaret.left, gui.rcCaret.top)
                                user32.ClientToScreen(gui.hwndCaret, ctypes.byref(pt))
                                caret_rect = (pt.x, pt.y, pt.x + max(w, 4), pt.y + max(h, 18))
                                return True, caret_rect
                return False, None

            # 3. Microsoft Word Fallback (OpusApp)
            if "opusapp" in fg_cls:
                tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
                if tid:
                    gui = GUITHREADINFO()
                    gui.cbSize = ctypes.sizeof(GUITHREADINFO)
                    if user32.GetGUIThreadInfo(tid, ctypes.byref(gui)):
                        if gui.hwndFocus and user32.IsWindow(gui.hwndFocus):
                            user32.GetClassNameW(gui.hwndFocus, buf, 256)
                            focus_cls = buf.value.lower()
                            if any(w in focus_cls for w in ("_wwg", "_wwb")):
                                if gui.hwndCaret and (gui.rcCaret.right > gui.rcCaret.left or gui.rcCaret.bottom > gui.rcCaret.top):
                                    pt = POINT(gui.rcCaret.left, gui.rcCaret.top)
                                    user32.ClientToScreen(gui.hwndCaret, ctypes.byref(pt))
                                    caret_rect = (pt.x, pt.y, pt.x + max(gui.rcCaret.right - gui.rcCaret.left, 4), pt.y + max(gui.rcCaret.bottom - gui.rcCaret.top, 18))
                                    return True, caret_rect
                                return True, None
                return False, None

            # 4. Native Win32 Caret Fallback (for non-Chromium apps with standard Edit/RichEdit)
            if not is_chromium_window:
                tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
                if tid:
                    gui = GUITHREADINFO()
                    gui.cbSize = ctypes.sizeof(GUITHREADINFO)
                    if user32.GetGUIThreadInfo(tid, ctypes.byref(gui)):
                        if gui.hwndFocus and user32.IsWindow(gui.hwndFocus):
                            user32.GetClassNameW(gui.hwndFocus, buf, 256)
                            focus_cls = buf.value.lower()
                            if any(k in focus_cls for k in WIN32_EDIT_CLASSES):
                                style = user32.GetWindowLongW(gui.hwndFocus, GWL_STYLE)
                                if not (style & ES_READONLY):
                                    if gui.hwndCaret and (gui.rcCaret.right > gui.rcCaret.left or gui.rcCaret.bottom > gui.rcCaret.top):
                                        pt = POINT(gui.rcCaret.left, gui.rcCaret.top)
                                        user32.ClientToScreen(gui.hwndCaret, ctypes.byref(pt))
                                        caret_rect = (pt.x, pt.y, pt.x + max(gui.rcCaret.right - gui.rcCaret.left, 4), pt.y + max(gui.rcCaret.bottom - gui.rcCaret.top, 18))
                                        return True, caret_rect
                                    rect = RECT()
                                    user32.GetWindowRect(gui.hwndFocus, ctypes.byref(rect))
                                    return True, (rect.left, rect.top, rect.right, rect.bottom)

            return False, None
        except Exception as e:
            return False, None

    def is_text_box_focused(self) -> bool:
        """Convenience method returning bool only."""
        return self.get_focused_text_input()[0]

    def _validate_element(self, ctrl) -> tuple[bool, tuple | None]:
        """
        Validates whether a UIA control is an editable text field according to strict criteria:
        1. ControlType is Edit, Document, or ComboBox (editable), OR has aria role textbox/searchbox
        2. IsKeyboardFocusable is true
        3. IsEnabled is true
        4. IsPassword is false
        5. ValuePattern.IsReadOnly is false, OR TextPattern/TextEditPattern is supported and editable.
        """
        if not ctrl:
            return False, None

        # Disabled elements are never editable
        if not getattr(ctrl, 'IsEnabled', True):
            return False, None

        # Password fields must remain hidden
        if getattr(ctrl, 'IsPassword', False):
            return False, None

        # Must be focusable
        if not getattr(ctrl, 'IsKeyboardFocusable', False):
            return False, None

        ctl_type = ctrl.ControlTypeName
        aria_role = (getattr(ctrl, 'AriaRole', '') or '').lower()
        ctrl_cls = (getattr(ctrl, 'ClassName', '') or '').lower()

        # Extract bounding rectangle if available
        rect = None
        try:
            brect = ctrl.BoundingRectangle
            if brect and (brect[2] > brect[0]) and (brect[3] > brect[1]):
                rect = (brect[0], brect[1], brect[2], brect[3])
        except Exception:
            pass

        # Static web document areas ("document", "webarea") are reading surfaces, NEVER editable text inputs.
        if aria_role in ("document", "webarea"):
            return False, None

        # Terminal controls (e.g. WezTerm, Windows Terminal, Alacritty)
        if any(term in ctrl_cls for term in TERMINAL_WINDOW_CLASSES):
            return True, rect

        is_target_type = (ctl_type in ("EditControl", "DocumentControl", "ComboBoxControl") or
                          aria_role in ("textbox", "searchbox"))
        if not is_target_type:
            return False, None

        # Case A: EditControl (Universal text inputs, search boxes, textareas, Omnibox)
        if ctl_type == "EditControl":
            val_pat = ctrl.GetPattern(auto.PatternId.ValuePattern)
            if val_pat:
                try:
                    is_ro = getattr(val_pat, 'CurrentIsReadOnly', getattr(val_pat, 'IsReadOnly', False))
                    if is_ro:
                        return False, None
                except Exception:
                    pass

            hwnd = getattr(ctrl, 'NativeWindowHandle', 0)
            if hwnd and user32.IsWindow(hwnd):
                style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                if style & ES_READONLY:
                    return False, None
            return True, rect

        # Case B: DocumentControl (Web views, rich editors, Word)
        # Static webpages (articles, chess boards, social feeds) are DocumentControl WITHOUT editability.
        if ctl_type == "DocumentControl":
            # Microsoft Word document edit pane
            if any(w in ctrl_cls for w in ("_wwg", "_wwb", "_wwf")):
                return True, rect

            # Browser host window containers are never text inputs
            if any(c in ctrl_cls for c in ("chrome_renderwidgethost", "webview")):
                return False, None

            # ValuePattern check: if present and marked read-only, it is NOT editable
            val_pat = ctrl.GetPattern(auto.PatternId.ValuePattern)
            if val_pat:
                try:
                    is_ro = getattr(val_pat, 'CurrentIsReadOnly', getattr(val_pat, 'IsReadOnly', False))
                    if is_ro:
                        return False, None
                except Exception:
                    pass

            # LegacyIAccessiblePattern check: if read-only flag is set, it is NOT editable
            leg = ctrl.GetPattern(auto.PatternId.LegacyIAccessiblePattern)
            if leg:
                try:
                    if getattr(leg, 'State', 0) & STATE_SYSTEM_READONLY:
                        return False, None
                except Exception:
                    pass

            # Explicit textbox / searchbox aria role (e.g. web rich text editors)
            if aria_role in ("textbox", "searchbox"):
                return True, rect

            # Native desktop rich text editors (WordPad, etc.) that support TextEditPattern
            if ctrl.GetPattern(auto.PatternId.TextEditPattern) is not None:
                if val_pat and not getattr(val_pat, 'CurrentIsReadOnly', getattr(val_pat, 'IsReadOnly', False)):
                    return True, rect

            # Legacy text role without read-only
            if leg:
                try:
                    if getattr(leg, 'Role', 0) == ROLE_SYSTEM_TEXT:
                        if not (getattr(leg, 'State', 0) & STATE_SYSTEM_READONLY):
                            return True, rect
                except Exception:
                    pass
            return False, None

        # Case C: ComboBoxControl (editable combobox / search dropdowns)
        if ctl_type == "ComboBoxControl":
            val_pat = ctrl.GetPattern(auto.PatternId.ValuePattern)
            if val_pat:
                try:
                    is_ro = getattr(val_pat, 'CurrentIsReadOnly', getattr(val_pat, 'IsReadOnly', False))
                    if is_ro:
                        return False, None
                    return True, rect
                except Exception:
                    pass
            if aria_role in ("textbox", "searchbox"):
                return True, rect
            return False, None

        # Case D: Custom elements with explicit textbox/searchbox aria role
        if aria_role in ("textbox", "searchbox"):
            val_pat = ctrl.GetPattern(auto.PatternId.ValuePattern)
            if val_pat:
                try:
                    if getattr(val_pat, 'CurrentIsReadOnly', getattr(val_pat, 'IsReadOnly', False)):
                        return False, None
                except Exception:
                    pass
            return True, rect

        return False, None
