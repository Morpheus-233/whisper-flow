# Milestone M3 Adversarial Challenge Report

**Target**: Milestone M3 (Unified Settings UI & Floating Capsule Badges)  
**Worker**: `worker_m3_it1`  
**Challenger**: `challenger_m3_1`  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

Direct empirical observations from codebase inspection, unit tests, Hinglish benchmarks, and dedicated adversarial stress harness (`tests/test_m3_empirical_challenger.py`):

1. **Test Suite Baseline**:
   - `.\.venv\Scripts\python.exe -m unittest -v tests/test_settings_ui_r2.py`
     - 16/16 tests passed in 0.342s.
   - `.\.venv\Scripts\python.exe -m unittest discover tests`
     - 237/237 tests passed in 7.156s.
   - `.\.venv\Scripts\python.exe benchmark_hinglish.py`
     - 20/20 test cases passed (100.0% pass rate) with Mean CPU latency: 6.18ms - 9.25ms (Budget: <200ms).

2. **1-Click Dictionary Word & Replacement Rule Removal Performance (<1ms SLA)**:
   - Measured across 50 sequential word deletions via `_on_remove_word_clicked(w)`:
     ```
     Mean: 0.3120 ms | Min: 0.2586 ms | Max: 0.4462 ms | P95: 0.4013 ms
     ```
   - Measured across 50 sequential rule deletions via `_on_remove_rep_clicked(h)`:
     ```
     Mean: 0.3238 ms | Min: 0.2723 ms | Max: 0.5099 ms | P95: 0.4055 ms
     ```
   - Both strictly satisfy the `<1ms` SLA. Edge cases (non-existent word, hidden filtered item, special unicode/Devanagari characters) completed safely in sub-millisecond time.

3. **Floating Capsule Dock Geometry (148x34px) & Concurrent Signals**:
   - `FloatingWidget` idle geometry invariants: `self.dock_w = 148`, `self.dock_h = 34`, total size `162x46` (with `pad_x=7`, `pad_y=6`).
   - Center anchoring `(cx, cy)` strictly preserved across 20 rapid transitions between `STATE_IDLE` and `STATE_RECORDING`.
   - 150 concurrent status badge updates across multiple background threads completed with zero race conditions or Qt errors.
   - Offscreen rendering (`QPainter` on `QImage`) of `paintEvent` verified no clipping across all combinations of engine, language, and style.

4. **Non-Blocking API Connection Test & VU Meter Error Resilience**:
   - `_start_groq_ping_test()` returns control to the Qt GUI thread in `<15.0ms` while executing network I/O on a background daemon thread.
   - HTTP errors (401 Unauthorized, 429 Rate Limit, 500 Server Error, 503 Service Unavailable), DNS lookup failures (`URLError`), and timeouts are caught and display precise, styled status labels.
   - Early dialog close/rejection while the background thread is in-flight completes cleanly without segmentation faults or Qt object deletion errors.
   - VU meter audio polling clamps values to `[0, 100]`, resets to `0` on test completion or dialog rejection, and handles audio engine runtime exceptions without breaking the polling timer.

5. **CRITICAL FINDING: SettingsDialog Presentation Latency Violation (>50ms SLA)**:
   - Worker's benchmark in `test_settings_ui_r2.py:356-360` only measured instantiation `dlg = SettingsDialog(...)` and `dlg.close()`, which reported `~20.46ms`. It never called `dlg.show()` or `app.processEvents()`.
   - When empirically measuring real dialog presentation (`dlg.show()` + `app.processEvents()`):
     ```
     [M3 STRESS] SettingsDialog Full Presentation Latency (50 runs with show + processEvents):
       Mean: 76.77 ms - 257.58 ms | Min: 48.33 ms | Max: 715.86 ms | P95: 119.51 ms - 196.80 ms
     ```
   - Under a bloated profile (150 words + 150 rules):
     ```
     [M3 STRESS] Bloated Profile Presentation (150 words + 150 rules):
       Mean: 350.23 ms | Max: 386.89 ms
     ```
   - In `ui/settings_dialog.py`, line 445:
     ```python
     443:         self._dictionary_loaded = False
     444:         self.tabs.currentChanged.connect(self._on_tab_changed)
     445:         QTimer.singleShot(0, self._ensure_dictionary_loaded)
     ```
   - `QTimer.singleShot(0, self._ensure_dictionary_loaded)` schedules eager dictionary population on the very first event loop tick upon presentation.
   - `_ensure_dictionary_loaded()` calls `_refresh_vocab_list()` and `_refresh_rep_list()` (lines 830-906), creating compound `WordRowWidget` and `ReplacementRowWidget` instances for every saved word/rule and calling `setItemWidget(...)`. This takes `143.36ms+` on the main GUI thread, defeating the intended deferred loading on Tab 2.
   - When line 445 is removed and dictionary loading is deferred until Tab 2 is clicked (`_on_tab_changed(index=2)` at lines 819-822):
     ```
     Mean Presentation Latency: 41.04 ms (Min: 33.82 ms, Max: 68.51 ms)
     ```
     Presentation latency drops back below the 50ms SLA.

---

## 2. Logic Chain

1. From Observation 1, the baseline test suites (`test_settings_ui_r2.py`, `discover tests`, `benchmark_hinglish.py`) execute and pass under normal non-adversarial conditions.
2. From Observation 2, 3, and 4, the 1-click removal latency (<1ms), capsule dock sizing (148x34px), concurrent signal handling, non-blocking API ping, and VU meter error handling operate robustly and satisfy their respective specifications.
3. However, from Observation 5, the requirement in `ORIGINAL_REQUEST.md` (R3 / Acceptance Criteria: "Preferences and Voice Calibration dialogs open in under 50ms") is violated in real presentation scenarios.
4. The worker claimed in `worker_m3_it1/handoff.md:29` that deferred tab loading was preserved with open latency benchmarked at `10.03ms - 22.01ms`. But tracing the code in `ui/settings_dialog.py:445` reveals `QTimer.singleShot(0, self._ensure_dictionary_loaded)`.
5. Because `singleShot(0)` is registered during `__init__`, calling `show()` and processing Qt events immediately triggers `_ensure_dictionary_loaded()`, instantiating dozens of compound QWidgets and running stylesheet evaluations on the main GUI thread before the user ever touches the dictionary tab.
6. Empirical benchmarking across 50 runs demonstrated actual presentation latency of `76.77ms - 257.58ms` (mean) and `350.23ms` under a bloated profile, failing the `<50ms` SLA constraint.
7. Deferring `_ensure_dictionary_loaded()` strictly to tab switch (`_on_tab_changed` index 2) or direct dictionary actions (already defensively wired in `_filter_vocab_list`, `_add_custom_word`, etc.) restores mean presentation latency to `41.04ms` (<50ms).
8. Therefore, Milestone M3 cannot be approved until line 445 in `ui/settings_dialog.py` is removed and true deferred loading is verified.

---

## 3. Caveats

- All adversarial tests were executed on local Windows 10 environment (Python 3.12, PySide6).
- The network tests for Groq API ping used mocking (`unittest.mock.patch`) to simulate network conditions (delays, timeouts, HTTP 401/429/500/503) deterministically without consuming live API tokens or requiring network connectivity.
- No production application code was modified by this challenger agent in accordance with the review-only role constraint.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone M3 satisfies functional, layout, badge, and audio/network diagnostics requirements, but fails the sub-50ms dialog presentation SLA due to eager dictionary loading scheduled via `QTimer.singleShot(0, self._ensure_dictionary_loaded)`:

### Required Action for Worker (`worker_m3_it1`):
1. In `ui/settings_dialog.py`, remove line 445:
   ```python
   # Line 445 to remove:
   QTimer.singleShot(0, self._ensure_dictionary_loaded)
   ```
2. Verify that `_on_tab_changed` (line 819) continues to lazily load the dictionary on first access to Tab 2 (`Personal Dictionary`).
3. Re-run `.\.venv\Scripts\python.exe -m unittest -v tests/test_m3_empirical_challenger.py` and confirm that all 15 stress tests pass with full presentation latency strictly `<50ms`.

---

## 5. Verification Method

To independently verify this finding:

1. **Run the Adversarial Stress Test Suite**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest -v tests/test_m3_empirical_challenger.py
   ```
   *Current Result*: Fails on `test_settings_dialog_full_presentation_latency_50_runs` (`mean=76.77ms - 257.58ms > 50ms`) and `test_settings_dialog_bloated_profile_presentation` (`mean=350.23ms > 50ms`).

2. **Verify Sub-50ms Latency Upon Removing Line 445**:
   Run dry-run profiling without `singleShot(0)`:
   ```powershell
   .\.venv\Scripts\python.exe -c "import time, sys; from PySide6.QtWidgets import QApplication; app = QApplication.instance() or QApplication(sys.argv); from unittest.mock import MagicMock; from config import load_config; from ui.settings_dialog import SettingsDialog; cfg = load_config(); audio = MagicMock(); whisper = MagicMock(); from PySide6.QtCore import QTimer; QTimer.singleShot = lambda ms, cb: None; latencies = [(t0:=time.perf_counter(), (dlg:=SettingsDialog(cfg, audio, whisper)).show(), app.processEvents(), (time.perf_counter()-t0)*1000.0, dlg.close(), app.processEvents())[3] for _ in range(20)]; print(f'Mean Presentation Latency: {sum(latencies)/len(latencies):.2f}ms')"
   ```
   *Expected Outcome*: Mean presentation latency drops to ~41ms (<50ms).

3. **Verify Regression Suites**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest -v tests/test_settings_ui_r2.py
   .\.venv\Scripts\python.exe -m unittest discover tests
   .\.venv\Scripts\python.exe benchmark_hinglish.py
   ```
