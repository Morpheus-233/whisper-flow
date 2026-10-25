## 2026-10-22T11:09:54Z
You are Worker M1 (Iteration 2 Remediation) for Whisper Flow Round 2.
Your working directory is: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m1_it2
Authoritative user request: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md (specifically see ## 2026-10-22T09:54:41Z).
Project architecture: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your exclusive write ownership:
- style_engine.py
- voice_profile.py
- whisper_engine.py
- text_cleaner.py
- tests/test_e2e_workflows.py

Your task:
Apply the verified drop-in code fixes documented by the three M1 fix explorers to address all 8 failures in tests/test_m1_round2_adversarial.py:
1. style_engine.py:
   - Add independent Candra vowels ('ऑ': 'o', 'ऍ': 'e', 'ॲ': 'a', 'ऎ': 'e', 'ऒ': 'o', 'ः': 'h') to FastDevanagariRomanizer.VOWELS.
   - Add 'ॆ': 'e', 'ॊ': 'o' to MATRAS. Add 'ळ': 'l' to CONSONANTS.
   - Add 'ऑप्शन': 'option', 'ऑनलाइन': 'online', 'ऑब्जेक्ट': 'object', 'ॲप': 'app', 'दुःख': 'dukh', 'अतः': 'atah', 'पुनः': 'punah' to DEV_COMMON_WORDS.
   - In transliterate_token:
     * Strip invisible ZWJ (\u200d) and ZWNJ (\u200c) upfront and before return.
     * Handle decomposed Candra vowels (अ + \u0949 -> 'o', अ + \u0945 -> 'e').
     * Handle Visarga after consonant (\u0903 -> base + 'ah') and standalone Visarga (\u0903 -> 'h').
     * Handle \u0964 and \u0965 before consonant or punctuation.
   - In romanize:
     * Strip \u200c and \u200d.
     * Split tokens using re.split(r'(\s+|[^\w\u0900-\u0963\u0966-\u097F]+)', text) so Devanagari Danda (\u0964) and Double Danda (\u0965) are delimiters and do not mangle dictionary terms.
   (See C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_m1_fix_1\handoff.md and explorer_m1_fix_2\handoff.md)

2. voice_profile.py:
   - In apply_replacements:
     * Use word boundary lookarounds that treat \u0964 and \u0965 as punctuation rather than word characters:
       DEV_W = r'[\w\u0900-\u0963\u0966-\u097F]'
       lb = rf'(?<!{DEV_W})', rb = rf'(?!{DEV_W})'
     * To scale cleanly up to 2000 rules in <2000ms, group sorted keys into composite boundary buckets (both boundaries, start only, end only, none) or single precompiled regex. (See explorer_m1_fix_2\handoff.md and explorer_m1_fix_3\handoff.md).

3. whisper_engine.py:
   - In transcribe():
     * Ensure Stage 3 VoiceProfileManager.apply_replacements is executed unconditionally even when style is None (after FastDevanagariRomanizer converts any Devanagari in raw_text). (See explorer_m1_fix_3\handoff.md).

4. text_cleaner.py:
   - In format_casual_chat():
     * If the text consists purely of punctuation with no word characters (not re.search(r'[\w\u0900-\u097F]', text)), return "" to collapse pure punctuation. (See explorer_m1_fix_3\handoff.md).

5. tests/test_e2e_workflows.py:
   - In test_simulated_zero_gpu_dictation_pipeline, isolate mgr.profile["word_replacements"] with a fixture save/restore to prevent on-disk profile interference when style=None.

Verification:
Execute and document output of:
1. .\.venv\Scripts\python.exe -m unittest tests/test_m1_round2_adversarial.py (all 20 must pass!)
2. .\.venv\Scripts\python.exe -m unittest discover tests (all 201+ tests must pass!)
3. .\.venv\Scripts\python.exe benchmark_hinglish.py (20/20 pass!)

Write progress in progress.md, detailed report in handoff.md in your working directory, and call send_message when complete.
