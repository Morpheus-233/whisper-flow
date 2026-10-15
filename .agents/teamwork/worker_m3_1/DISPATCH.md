# Dispatch: Worker M3 (Desktop Lifecycle, Mutex IPC & UI Responsiveness)

**Role**: Desktop Lifecycle & UI Responsiveness Worker
**Type**: teamwork_preview_worker
**Working Directory**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m3_1
**Project Root**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
**Original Request**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md
**Project Scope Document**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md

## Exclusive Write Ownership
You exclusively own:
- `app.py`
- `ui/floating_widget.py`
- `ui/settings_dialog.py`
- `ui/theme_helper.py`

## Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Objectives
1. Read ORIGINAL_REQUEST.md and PROJECT.md carefully.
2. Review Survey Spec Miner 3 and Explorer 1 handoffs:
   - `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\spec_miner_survey_3\handoff.md`
   - `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_1\handoff.md`

3. **Fast-Path Single-Instance Mutex Check (<100ms Exit) in `app.py`**:
   - Hoist the named mutex check (`Local\WhisperFlow_SingleInstance_Mutex_v3`) to the top of `app.py` *before* importing heavy modules (`faster_whisper`, `torch`, `focus_detector`, `PySide6`).
   - Use pure `ctypes` (`kernel32.CreateMutexW`).
   - If `GetLastError() == 183` (`ERROR_ALREADY_EXISTS`):
     - Call `user32.AllowSetForegroundWindow(0xFFFFFFFF)`.
     - Register and post `WM_SHOW_WHISPER_FLOW` via `user32.PostMessageW(0xFFFF, ...)`.
     - Send `SHOW\n` through Qt IPC or socket if achievable quickly, or rely on Win32 broadcast.
     - Call `sys.exit(0)` immediately.
     - Verify execution time: must exit in <100ms (survey benchmark showed ~60ms).

4. **Foreground Activation & Preferences Raising in `app.py`**:
   - In `show_widget_requested()` / IPC handler:
     - Bring floating capsule to front, clear any minimized state, raise window, call `user32.SetForegroundWindow`.
     - Open Preferences dialog front-and-center, ensuring it receives active focus.

5. **Sub-50ms Dialog Presentation & UI Responsiveness in `ui/settings_dialog.py`**:
   - Eliminate cold startup lag (previously 142ms) caused by eager synchronous instantiation of 42 custom composite widgets in Tab 2.
   - Defer row widget creation in the Personal Dictionary tab (e.g. load on tab switch or via `QTimer.singleShot(0, ...)`), or pre-warm dialog instances, ensuring `SettingsDialog` presentation latency is strictly <50ms.
   - **1-Click Instant Removal**: Ensure deleting a custom word or replacement executes in 0ms without rebuilding the entire list (`takeItem` in-place).
   - **Real-Time Search Filtering**: Toggle item visibility (`item.setHidden(not matches)`) on keystrokes instead of clearing and rebuilding all widgets.

6. **Win32 Mouse Capture Safety & Theme Helper**:
   - In `ui/floating_widget.py` and `ui/settings_dialog.py`: ensure explicit `user32.ReleaseCapture()` before mouse drags, context menus, and modal dialog launches to avoid Win32 mouse capture deadlock.
   - In `ui/theme_helper.py`: verify native DWM immersive dark mode (`DWMWA_USE_IMMERSIVE_DARK_MODE = 20` with fallback 19) and `#0f172a` palette.

7. **Verification**:
   - Run tests: `.\.venv\Scripts\python.exe -m unittest discover tests`.
   - Benchmark second-instance exit latency: verify <100ms when mutex is held.
   - Benchmark SettingsDialog open latency: verify <50ms.
   - Write handoff report to `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m3_1\handoff.md`.
   - Send completion message to orchestrator.


## 2026-10-15T15:36:02Z
You are Worker M3 (Desktop Lifecycle, Mutex IPC & UI Responsiveness).
Your working directory is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m3_1
The project root is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
Read C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md, C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md, and your dispatch at C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m3_1\DISPATCH.md before starting.
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
You exclusively own app.py, ui/floating_widget.py, ui/settings_dialog.py, and ui/theme_helper.py.
Implement:
1. Fast-path named mutex check at top of app.py before heavy module imports (exits in <100ms with AllowSetForegroundWindow and show signal).
2. Foreground activation & Preferences raising in app.py.
3. Sub-50ms dialog presentation in SettingsDialog (deferred/lazy dictionary rows), 1-click instant removal (takeItem in-place), and real-time in-place search filtering (item.setHidden).
4. Win32 mouse capture deadlock prevention (ReleaseCapture) and DWM immersive dark mode.
Verify with .\.venv\Scripts\python.exe -m unittest discover tests and timing benchmarks.
Write handoff.md in your working directory and notify the orchestrator when complete.
