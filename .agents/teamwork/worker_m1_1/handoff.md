# Milestone 1 Handoff: Bilingual Calibration & Phonetic Mapper

## 1. Observation
1. **Calibration Dataset Verification**:
   - Path: `data/calibration_sentences.json` (24,115 bytes, 981 lines).
   - Validated: 100 sentences with sequential IDs 1 to 100, exactly 50 `"english"` and 50 `"hindi_hinglish"`. All entries contain `"id"`, `"category"`, `"text"`, and non-empty `"phonetic_keywords"`.
2. **Diff Engine & Punctuation Leakage Before Fix**:
   - `studio_server.py` lines 102-106 previously sliced raw tokens without punctuation stripping (`t_chunk = " ".join(target_tokens[i1:i2])`), creating misheard pairs with trailing periods (e.g., target `"hoon."` for heard `"hu"`).
   - `calibration_engine.py` was implemented as a standalone pure module with zero heavy imports (no PySide6, torch, or faster-whisper).
   - `strip_punctuation` cleans leading/trailing punctuation while preserving internal hyphens, apostrophes, and spaces.
   - For target `"Main thodi der mein call karta hoon."` and heard `"main thodi der me call karta hu"`:
     - `accuracy`: `71.4%` (clamped 0.0 - 100.0).
     - `misheard_pairs`: `[{'heard': 'me', 'target': 'mein'}, {'heard': 'hu', 'target': 'hoon'}]` (clean without trailing period).
     - `missing_keywords`: `['call karta hoon']`.
3. **Regex Boundary Flaw in `voice_profile.py` Before Fix**:
   - Line 147 in `voice_profile.py` previously used `r'\b(' + '|'.join(escaped_keys) + r')\b'`.
   - In `voice_profile.json`, `"cooper nets,": "Kubernetes"` has a trailing comma `,` (`\W`). Because `,` followed by whitespace is a `\W`-to-`\W` transition, `\b` failed to match, preventing `"Kubernetes"` replacement during dictation.
   - Upgraded to conditional lookaround boundaries `(?<!\w)` at token start and `(?!\w)` at token end.
   - Tested: `'I manage cooper nets, in our cloud infrastructure.'` -> successfully replaced with `'I manage Kubernetes in our cloud infrastructure.'`.
   - Added token budget truncation (`max_chars=800`) to `VoiceProfileManager.get_initial_prompt()` to safeguard Whisper's ~224 token decoding window.
4. **Voice Training Dialog Integration**:
   - `ui/voice_training_dialog.py` previously hardcoded 3 English sentences and lacked diffing or mapping.
   - Replaced with dynamic dataset loading (`CALIBRATION_DATASET = load_calibration_dataset()`, 100 sentences).
   - Added interactive language filtering (`All (100)`, `English (50)`, `Hindi / Hinglish (50)`).
   - Integrated `compute_diff` and `auto_register_misheard_pairs` on transcription: misheard phonetic pairs are automatically saved into `voice_profile.json` and immediate feedback is displayed.
   - Dialog initialization latency: `45.66 ms` (< 50ms requirement satisfied).
5. **Test Suite Verification**:
   - Running `.\.venv\Scripts\python.exe -m unittest tests/test_speech_calibration.py` executed 14 tests in 0.005s with status `OK`.

## 2. Logic Chain
- *Step 1 (Dataset)*: From Observation 1, `data/calibration_sentences.json` contains the required 100 bilingual sentences with valid schema.
- *Step 2 (Diff Engine)*: Observation 2 showed raw token slicing caused punctuation leaks into replacement keys. Extracting diff logic into `calibration_engine.py` with `strip_punctuation` ensures misheard pairs like `"hu"` map to clean `"hoon"`, preventing corrupt punctuation in subsequent dictation.
- *Step 3 (Phonetic Mapper & Regex)*: Observation 3 revealed that `\b` fails on keys with trailing punctuation. Conditional lookarounds `(?<!\w)` and `(?!\w)` assert boundary boundaries only for alphanumeric characters, enabling clean multi-word and punctuation-laden substitutions (`"cooper nets,"` -> `"Kubernetes"`) while preventing nested substring replacements.
- *Step 4 (UI Wizard)*: Observation 4 verified that loading all 100 sentences in `VoiceTrainingDialog` alongside real-time SequenceMatcher diffing enables instant feedback and automated registration of Hinglish misheard words into `voice_profile.json`.
- *Step 5 (Performance)*: Initializing dataset at module load keeps `VoiceTrainingDialog` presentation latency at 45.66ms (< 50ms requirement).

## 3. Caveats
- `tests/test_ui_responsiveness.py` has an unrelated failure in `test_mouse_capture_deadlock_prevention` due to `FloatingWidget` constructor arguments, which is owned by Worker M3.
- In `VoiceTrainingDialog`, recording requires an active audio input device when run interactively; headless unit testing was executed with mocked and synthetic signals.

## 4. Conclusion
Milestone M1 objectives are 100% complete and verified:
- `calibration_engine.py`: Implemented standalone diffing, accuracy clamping, punctuation-clean pairs, dataset loading, and auto-registration.
- `voice_profile.py`: Lookaround regex boundaries fixed; safe initial prompt truncation implemented.
- `ui/voice_training_dialog.py`: 100 bilingual sentences loaded; interactive category filtering, diffing, and automated phonetic pair registration integrated.
- `data/calibration_sentences.json`: Validated 100-sentence bilingual corpus.
- All 14 tests in `tests/test_speech_calibration.py` pass cleanly.

## 5. Verification Method
1. **Run Unit Tests for Speech Calibration**:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest tests/test_speech_calibration.py
   ```
   *Expected output: `Ran 14 tests in 0.005s` / `OK`.*

2. **Verify Lookaround Regex Boundary Replacement**:
   ```powershell
   .\.venv\Scripts\python.exe -c "from voice_profile import VoiceProfileManager; mgr = VoiceProfileManager.get_instance(); assert mgr.apply_replacements('I manage cooper nets, in cloud') == 'I manage Kubernetes in cloud'; print('Regex verified!')"
   ```

3. **Verify VoiceTrainingDialog Initialization Latency & Dataset**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import sys, time; from PySide6.QtWidgets import QApplication; app = QApplication.instance() or QApplication(sys.argv); from ui.voice_training_dialog import VoiceTrainingDialog, CALIBRATION_SENTENCES; assert len(CALIBRATION_SENTENCES) == 100; t0 = time.time(); dlg = VoiceTrainingDialog(None, None); print(f'Init: {(time.time()-t0)*1000:.2f}ms'); assert len(dlg.calibration_dataset) == 100"
   ```

4. **Verify Zero Heavy Dependencies in `calibration_engine.py`**:
   ```powershell
   .\.venv\Scripts\python.exe -c "import sys, calibration_engine; mods = list(sys.modules.keys()); assert not any('PySide6' in m or 'faster_whisper' in m or 'torch' in m for m in mods); print('Zero heavy dependencies verified!')"
   ```
