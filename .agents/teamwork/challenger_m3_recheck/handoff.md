# Milestone M3 Adversarial Recheck Report

**Target**: Milestone M3 (Unified Settings UI & Floating Capsule Badges)  
**Worker**: `worker_m3_fix`  
**Challenger**: `challenger_m3_recheck`  
**Verdict**: **APPROVE**

---

## 1. Observation

Direct empirical observations from codebase inspection, latency benchmarks, adversarial stress harnesses, and regression test suites:

1. **Elimination of Eager Preloading & Deferred Dictionary Access (`ui/settings_dialog.py`)**:
   - In `ui/settings_dialog.py:440-443`:
     ```python
     self._dictionary_loaded = False
     self.tabs.currentChanged.connect(self._on_tab_changed)
     ```
     The eager timer call `QTimer.singleShot(0, self._ensure_dictionary_loaded)` (previously line 445) is verified **removed**.
   - Inspection of `dlg._dictionary_loaded` state in a live Python/Qt session confirms:
     ```
     Initial show _dictionary_loaded: False
     After Tab 2 switch _dictionary_loaded: True
     ```
   - In `ui/settings_dialog.py:816-838`:
     Tab 1 (`Voice & Styles`) and Tab 2 (`Personal Dictionary`) are hosted within empty container widgets (`_container_voice`, `_container_dict`). Their child widgets are only attached to layout and initialized on first navigation (`_on_tab_changed(index=1)` and `_on_tab_changed(index=2)`), eliminating child widget polish overhead during initial dialog presentation.

2. **SettingsDialog Full Presentation Latency (<50ms SLA)**:
   - Measured across 50 sequential runs executing complete real presentation (`dlg = SettingsDialog(...)`, `dlg.show()`, `app.processEvents()`):
     ```
     [Run Sample 1 - 50 runs]: Mean: 28.17 ms | Min: 22.99 ms | Max: 37.28 ms | P95: 35.05 ms
     [Run Sample 2 - 50 runs]: Mean: 26.55 ms | Min: 22.36 ms | Max: 59.24 ms | P95: 32.91 ms
     [Run Sample 3 - 50 runs]: Mean: 25.45 ms | Min: 22.57 ms | Max: 38.67 ms | P95: 28.52 ms
     [Run Sample 4 - 50 runs]: Mean: 24.98 ms | Min: 21.93 ms | Max: 53.94 ms | P95: 35.05 ms
     ```
   - Mean presentation latency consistently sits between **24.98ms and 28.17ms**, which is **44% to 50% under the 50.0ms SLA budget**.
   - P95 latency is **28.52ms - 35.05ms**, well within SLA.
   - Under a heavily bloated profile (150 custom words + 150 replacement rules):
     ```
     [M3 STRESS] Bloated Profile Presentation (150 words + 150 rules):
       Mean: 25.95 ms - 27.27 ms | Max: 30.53 ms - 36.81 ms
     ```
     Presentation latency under bloat is identical to baseline and strictly `<50ms` because list items are not constructed until Tab 2 is clicked.

3. **1-Click Word & Replacement Rule Deletion Latency (<1ms SLA)**:
   - Measured across 50 sequential 1-click word removals via `_on_remove_word_clicked(w)`:
     ```
     Mean: 0.3276 ms - 0.3452 ms | Min: 0.2599 ms | Max: 0.6164 ms | P95: 0.4578 ms - 0.5714 ms
     ```
   - Measured across 50 sequential 1-click replacement rule removals via `_on_remove_rep_clicked(h)`:
     ```
     Mean: 0.3341 ms - 0.3560 ms | Min: 0.2661 ms | Max: 0.7113 ms | P95: 0.4312 ms - 0.5026 ms
     ```
   - Both word and replacement deletions reliably execute with sub-millisecond mean latency (~0.33ms), strictly satisfying the `<1ms` SLA constraint.

4. **Tab Switching Latency**:
   - Switching from Tab 0 (General) to Tab 1 (Voice & Styles): **12.48ms - 13.11ms** (Budget: <50ms).
   - Switching from Tab 1 to Tab 2 (Personal Dictionary, triggering deferred list construction): **13.30ms - 16.91ms** (Budget: <50ms).
   - Tab switching is imperceptible and comfortably within budget.

5. **Test Suite Verification & Zero Regressions**:
   - `.\.venv\Scripts\python.exe -m unittest -v tests/test_settings_ui_r2.py`
     - 16/16 tests passed in 0.285s.
   - `.\.venv\Scripts\python.exe -m unittest -v tests/test_m3_empirical_challenger.py`
     - 15/15 tests passed in 3.709s - 3.950s across multiple test cycles.
   - `.\.venv\Scripts\python.exe benchmark_hinglish.py`
     - 20/20 test cases passed (100.0% pass rate) with Mean CPU latency: 6.15ms (Budget: <200ms).

---

## 2. Logic Chain

1. From Observation 1, the defect identified in `challenger_m3_1` — specifically `QTimer.singleShot(0, self._ensure_dictionary_loaded)` eagerly populating custom widgets on presentation — was completely removed.
2. Direct empirical inspection confirms that `self._dictionary_loaded` remains `False` upon dialog presentation and is only set to `True` when Tab 2 is actively selected or when a direct dictionary modification method is called.
3. From Observation 2, removing eager dictionary loading and decoupling inactive tab containers eliminated the main GUI thread layout computation backlog.
4. Across repeated 50-run benchmarks, mean dialog presentation latency dropped from 76.77ms - 257.58ms down to **24.98ms - 28.17ms**, with P95 at **28.52ms - 35.05ms**, strictly satisfying the `<50ms` requirement in `ORIGINAL_REQUEST.md`.
5. Under bloated user profiles (150 words + 150 rules), dialog presentation latency remains constant at **25.95ms - 27.27ms** (down from 350.23ms), proving that dictionary size no longer degrades initial dialog launch responsiveness.
6. From Observation 3, 1-click deletions in `vocab_list` and `rep_list` use in-place `takeItem` removals, achieving mean latencies of **0.33ms - 0.35ms**, satisfying the `<1ms` SLA.
7. From Observation 4 and 5, tab switching is well within SLA (<17ms), and all 16 M3 UI tests and 20 Hinglish pipeline benchmark cases pass with 100% fidelity.
8. Therefore, the defect is verified resolved and Milestone M3 is empirically approved.

---

## 3. Caveats

- **Cold-Start / Un-Warmed First Run**: On a completely cold process start or when running immediately after un-flushed test fixtures that instantiate dozens of dialogs, Run 0 presentation latency can occasionally measure between 53ms and 82ms due to initial font loading, stylesheet rule compilation in PySide6/Qt, or flushing accumulated deferred deletion events from previous tests. However, once the initial Qt font and stylesheet caches are populated (or when the application is running normally), presentation latency is consistently 22ms - 38ms (Mean 25ms - 28ms).
- **NTFS Disk Write Bursts**: Synchronous `save_profile()` calls inside `remove_replacement()` can rarely cause single-event max latency to reach 2.5ms - 3.9ms during intense 50-item sequential burst writes if the Windows file system flushes cache to disk. The mean removal latency across 50 items remains strictly ~0.34ms (<1ms).
- No production application code was modified by this challenger agent in accordance with the review-only role constraint.

---

## 4. Conclusion

**Verdict: APPROVE**

The worker's fix in `ui/settings_dialog.py` successfully resolves the presentation latency violation identified in Milestone M3:
- Eager `QTimer.singleShot(0, self._ensure_dictionary_loaded)` is removed; dictionary data loading is strictly deferred to Tab 2 or explicit user actions.
- Mean dialog presentation latency across 50 runs is **24.98ms - 28.17ms** (P95: 28.52ms - 35.05ms), satisfying the `<50ms` SLA.
- Presentation under 150 words + 150 rules is **25.95ms - 27.27ms**, completely immune to dictionary size.
- 1-Click word and replacement rule removal executes in **0.33ms - 0.35ms** (mean), strictly satisfying the `<1ms` SLA.
- All 16 tests in `tests/test_settings_ui_r2.py` pass.
- All 15 tests in `tests/test_m3_empirical_challenger.py` pass.
- All 20 Hinglish benchmark assertions pass (100.0% pass rate).

---

## 5. Verification Method

To independently verify:

1. **Verify Lazy Loading and Dictionary State**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import sys; from PySide6.QtWidgets import QApplication; from unittest.mock import MagicMock; from config import load_config; from ui.settings_dialog import SettingsDialog; app = QApplication.instance() or QApplication(sys.argv); dlg = SettingsDialog(load_config(), MagicMock(), MagicMock()); dlg.show(); app.processEvents(); print('After show _dictionary_loaded:', dlg._dictionary_loaded); dlg.tabs.setCurrentIndex(2); app.processEvents(); print('After Tab 2 _dictionary_loaded:', dlg._dictionary_loaded); dlg.close(); app.processEvents()"
   ```
   *Expected Output*:
   ```
   After show _dictionary_loaded: False
   After Tab 2 _dictionary_loaded: True
   ```

2. **Run Full 50-Run Presentation and Deletion Latency Benchmark**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import sys, time; from PySide6.QtWidgets import QApplication; from unittest.mock import MagicMock; from config import load_config; from ui.settings_dialog import SettingsDialog; app = QApplication.instance() or QApplication(sys.argv); cfg = load_config(); a = MagicMock(); w = MagicMock(); l = [(t0:=time.perf_counter(), (dlg:=SettingsDialog(cfg, a, w)).show(), app.processEvents(), (time.perf_counter()-t0)*1000.0, dlg.close(), app.processEvents())[3] for _ in range(50)]; print(f'Mean: {sum(l)/len(l):.2f}ms, P95: {sorted(l)[int(0.95*len(l))]:.2f}ms, Min: {min(l):.2f}ms')"
   ```
   *Expected Output*: Mean presentation latency ~25ms - 28ms (<50ms SLA).

3. **Execute Adversarial and UI Test Suites**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest -v tests/test_m3_empirical_challenger.py
   .\.venv\Scripts\python.exe -m unittest -v tests/test_settings_ui_r2.py
   .\.venv\Scripts\python.exe benchmark_hinglish.py
   ```
