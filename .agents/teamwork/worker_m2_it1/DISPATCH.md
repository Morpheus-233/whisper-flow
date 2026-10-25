## 2026-10-22T11:25:42Z
You are Worker M2-1 for Whisper Flow Round 2 (Milestone M2: Smart Voice Calibration & Phonetic Memory).
Your working directory is: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m2_it1
Authoritative user request: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md (specifically see ## 2026-10-22T09:54:41Z).
Project architecture: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\PROJECT.md
Survey findings: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your exclusive write ownership:
- ui/voice_training_dialog.py
- voice_profile.py
- data/calibration_sentences.json

Your tasks:
1. ui/voice_training_dialog.py:
   - Implement `PhoneticPairChip(QWidget)` exported at module level:
     * `self.heard = heard`, `self.target = target`
     * `self.label = QLabel(f"'{heard}' → '{target}'")`
     * `self.btn_confirm = QPushButton("+ Remember")`
     * `self.btn_dismiss = QPushButton("✕")`
     * On confirm: calls `on_confirm(heard, target)`, registers mapping in profile, changes button text to `"✓ Remembered"`, disables confirm button.
     * On dismiss: calls `on_dismiss(heard, target)`, hides/removes widget.
     * Styled in modern dark theme (#1e293b card background, #3b82f6 accent).
   - In `_create_speech_page`:
     * Add `self.chips_container = QWidget()` with a horizontal/wrapping layout for candidate confirmation chips below `self.diff_status`.
   - In `_on_speech_finished`:
     * Clear old chips.
     * For each misheard pair in `diff_res.get("misheard_pairs", [])`:
       Instantiate `PhoneticPairChip` and add to `self.chips_container`.
       Define `on_confirm` to call `self.profile_mgr.add_replacement(heard, target)` and update UI status.
       Define `on_dismiss` to remove chip.
   - In `transcribe()` inside `_toggle_sentence_recording`:
     * If the recorded sentence is category `"hindi_hinglish"`, pass `text` through `FastDevanagariRomanizer.romanize(text)` if it contains Devanagari, so that Latin-to-Latin diffing is performed against the Romanized calibration target sentence.
   - In `_create_review_page`:
     * Add a list widget for Calibrated Phonetic Mappings (`self.profile_mgr.get_replacements()`) alongside custom words, supporting 1-click removal.
   - Ensure `VoiceTrainingDialog` initialization remains fast (<50ms).

2. voice_profile.py:
   - In `get_initial_prompt(max_chars=800)`:
     * Combine `custom_words` and unique target replacement words (`word_replacements.values()`).
     * Format as `"Vocabulary: " + ", ".join(included) + "."`, truncated to `max_chars=800`.
   - In `get_stage2_context() -> dict`:
     * Return `{"phonetic_memory": dict(self.get_replacements()), "custom_words": list(self.get_custom_words())}`.

3. data/calibration_sentences.json:
   - Verify sentence #87 (ID 87) has keyword `"demo"` instead of `"client demo"`.

Verification:
Execute and document output of:
1. .\.venv\Scripts\python.exe -m unittest tests/test_calibration_phonetic_memory.py
2. .\.venv\Scripts\python.exe -m unittest discover tests (all 218+ tests pass!)
3. .\.venv\Scripts\python.exe benchmark_hinglish.py (20/20 pass!)

Write progress in progress.md, detailed report in handoff.md in your working directory, and call send_message when complete.
