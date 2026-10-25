# Handoff Report: Milestone M2 — Smart Voice Calibration & Phonetic Memory

**Agent**: Worker M2-1 (`worker_m2_it1`)  
**Role**: Implementer / QA / Specialist  
**Parent**: Orchestrator R2 (`b7127cef-b446-4dca-a8e7-b0da25424e7e`)  
**Working Directory**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m2_it1`  
**Date**: 2026-10-22  

---

## 1. Observation

### Obs 1: PhoneticPairChip & Two-Stage Calibration in `ui/voice_training_dialog.py`
- **File**: `ui/voice_training_dialog.py` (lines 20–110, 410–435, 520–575, 600–740).
- **Direct observation**:
  - `PhoneticPairChip(QWidget)` is exported at module level (line 21):
    ```python
    class PhoneticPairChip(QWidget):
        def __init__(self, heard: str, target: str, on_confirm=None, on_dismiss=None, parent=None):
            ...
            self.heard = heard
            self.target = target
            self.label = QLabel(f"'{heard}' → '{target}'")
            self.btn_confirm = QPushButton("+ Remember")
            self.btn_dismiss = QPushButton("✕")
    ```
    - Styled in modern dark theme (`#1e293b` card background, `#3b82f6` accent button).
    - `_handle_confirm` registers replacement into `VoiceProfileManager`, executes `on_confirm(heard, target)`, changes text to `"✓ Remembered"`, and disables the button.
    - `_handle_dismiss` executes `on_dismiss(heard, target)` and hides widget (`self.hide()`).
  - `self.chips_container = QWidget()` and `self.chips_layout = QHBoxLayout` added below `self.diff_status` in `_create_speech_page`.
  - `_on_speech_finished` calls `self._clear_chips()`, extracts `diff_res.get("misheard_pairs", [])`, and instantiates `PhoneticPairChip` widgets with 1-click confirmation callbacks.
  - In `_toggle_sentence_recording`'s `transcribe()` function:
    ```python
    if target_item.get("category") == "hindi_hinglish" and FastDevanagariRomanizer.has_devanagari(text):
        text = FastDevanagariRomanizer.romanize(text)
    ```
    Spoken Hindi in Devanagari is transliterated into Romanized Latin script before diffing against Romanized calibration target sentences.
  - In `_create_review_page`, added a side-by-side layout featuring `self.word_list` (Custom Vocabulary) on the left and `self.replacements_list` (Calibrated Phonetic Mappings with `ReplacementRowWidget` supporting 1-click removal) on the right.
  - Deferred heavy row widget generation to page navigation (`_on_page_changed`), keeping `VoiceTrainingDialog` open latency at Mean = 12.61ms (well within the <50ms SLA).

### Obs 2: Dual Injection Contract in `voice_profile.py`
- **File**: `voice_profile.py` (lines 122–195).
- **Direct observation**:
  - `get_initial_prompt(max_chars=800, include_replacements=True)`:
    - Combines `clean_custom` words and unique target words from `self.get_replacements().values()`.
    - Returns `None` if custom words are empty/whitespace (conforming to edge-case unit test contracts).
    - Formats output as `"Vocabulary: " + ", ".join(included) + "."` bounded by `max_chars=800`.
  - `get_stage2_context()`:
    - Returns `{"phonetic_memory": all_reps, "custom_words": all_custom, "prompt_block": prompt_block}` where `all_reps = dict(self.get_replacements())` and `all_custom = list(self.get_custom_words())`.
    - Preserves `prompt_block` with XML `<personal_dictionary>` and `<phonetic_memory>` tags for `style_engine.py` Stage 2 LLM prompt injection.

### Obs 3: Sentence #87 Verification in `data/calibration_sentences.json`
- **File**: `data/calibration_sentences.json` (lines 844–853).
- **Direct observation**:
  - Sentence #87 has `id: 87`, `category: "hindi_hinglish"`, text `"Client ko demo dikhane se pehle edge cases thoroughly test kar lena."`, and `phonetic_keywords: ["demo", "edge cases", "thoroughly"]`.
  - Verified keyword is `"demo"`, matching the requirement.

### Obs 4: Test Suite & Benchmark Results
- **Command 1**: `.\.venv\Scripts\python.exe -m unittest tests/test_calibration_phonetic_memory.py`
  - Output: `Ran 10 tests in 0.037s` -> `OK`.
- **Command 2**: `.\.venv\Scripts\python.exe -m unittest discover tests`
  - Output: `Ran 218 tests in 4.932s` -> `OK`.
  - Benchmark details:
    - `[AC2 BENCHMARK] VoiceTrainingDialog Open Latency (5 runs): Mean=12.61ms, Min=7.84ms, Max=16.09ms` (Budget: <50ms)
    - `[AC5 BENCHMARK] 1-Click Word Removal Latency: 0.6009ms` (<1ms)
    - `[AC5 BENCHMARK] 1-Click Replacement Rule Removal Latency: 0.5138ms` (<1ms)
- **Command 3**: `.\.venv\Scripts\python.exe benchmark_hinglish.py`
  - Output: `Total Test Cases: 20 | Passed: 20 | Failed: 0 | Pass Rate: 100.0%`
  - Mean CPU Latency: `6.8360 ms` (Budget: <200ms)

---

## 2. Logic Chain

1. **Premise**: In `data/calibration_sentences.json`, all Hindi/Hinglish calibration targets are in Romanized Latin script. Spoken Hindi transcribed by Whisper often outputs Devanagari Unicode.
2. **Step**: Routing Hindi transcription through `FastDevanagariRomanizer.romanize()` when `target_item.get("category") == "hindi_hinglish"` produces Latin script output before calculating SequenceMatcher diffs (Obs 1).
3. **Inference**: Token diffs now operate in a single unified script (Latin-to-Latin), yielding high SequenceMatcher accuracy and clean misheard pairs without token mismatch.
4. **Premise**: Candidate misheard pairs should not be committed blindly without user agency.
5. **Step**: `ui/voice_training_dialog.py` presents misheard pairs as `PhoneticPairChip` widgets in `self.chips_container`. Clicking `+ Remember` triggers `on_confirm`, immediately updating `VoiceProfileManager` in <1ms, updating the UI badge to `"✓ Remembered"`, and updating review summary metrics (Obs 1).
6. **Premise**: Stage 1 token decoding in Whisper and Stage 2 LLM styling need access to calibrated vocabulary.
7. **Step**: `get_initial_prompt()` in `voice_profile.py` injects target pronunciation words into Whisper's initial prompt context, and `get_stage2_context()` returns full dictionary mappings and `<phonetic_memory>` blocks (Obs 2).
8. **Premise**: `VoiceTrainingDialog` must instantiate in <50ms. Eagerly generating 14+ row widgets with custom QSS in `__init__` previously caused latency spikes to ~53ms.
9. **Step**: Deferring list widget rendering until the review page is navigated to (`_on_page_changed`) eliminated widget churn on dialog open, dropping open latency from 53.29ms to 12.61ms (Obs 1, Obs 4).

---

## 3. Caveats

- **No caveats**: All 10 tests in `test_calibration_phonetic_memory.py`, all 218 repository tests, and all 20 benchmark tests passed cleanly with 0 errors and 0 failures.

---

## 4. Conclusion

Milestone M2 (Smart Voice Calibration & Phonetic Memory) is complete and verified:
1. `ui/voice_training_dialog.py`: `PhoneticPairChip` is exported and fully functional; `chips_container` presents candidate misheard pairs for 1-click confirmation (<1ms); Hindi speech is Romanized before diff computation; Step 3 review displays both Custom Vocabulary and Calibrated Phonetic Mappings with 1-click removal; dialog open latency is 12.61ms (<50ms budget).
2. `voice_profile.py`: `get_initial_prompt()` biases target replacement words in Whisper decoder up to 800 chars; `get_stage2_context()` provides structured `phonetic_memory` and `custom_words`.
3. `data/calibration_sentences.json`: Sentence #87 verified with keyword `"demo"`.

---

## 5. Verification Method

To independently reproduce verification:
```powershell
# 1. Run M2 test suite
.\.venv\Scripts\python.exe -m unittest tests/test_calibration_phonetic_memory.py

# 2. Run complete test suite (218+ tests)
.\.venv\Scripts\python.exe -m unittest discover tests

# 3. Run Hinglish benchmark suite (20/20 cases)
.\.venv\Scripts\python.exe benchmark_hinglish.py
```
- Invalidation condition: Any failure in `test_calibration_phonetic_memory.py`, any test failure across `tests/`, or dialog open latency exceeding 50ms.
