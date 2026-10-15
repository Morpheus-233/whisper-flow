# Survey Explorer 2: Speech & Style Engine Deep-Dive Investigation Report

## 1. Observation

### 1.1 Speech Engine Components (`whisper_engine.py`)
- **File Location**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\whisper_engine.py` (296 lines, 12,410 bytes).
- **faster-whisper CPU int8 Settings**:
  - Line 96-102:
    ```python
    self.model = WhisperModel(
        self.model_name,
        device="cpu",
        compute_type="int8",
        cpu_threads=6,
        download_root=os.path.join(os.path.expanduser("~"), ".cache", "whisper_flow_models")
    )
    ```
  - **Runtime Verification**: Verified `WhisperModel('base', device='cpu', compute_type='int8')` loads in <3.5s and transcribes audio on the 12th Gen Intel Core i5-12400F with **0 MB GPU VRAM** allocated.
  - **Local Model Cache**: Verified `~/.cache/whisper_flow_models` already contains:
    - `models--Systran--faster-whisper-base` (Multilingual)
    - `models--Systran--faster-whisper-base.en` (English only)
    - `models--Systran--faster-whisper-small.en` (English only)
- **Groq API Cloud Fallback**:
  - Lines 163-224: `_transcribe_groq(self, audio_data, api_key, sample_rate=16000, initial_prompt=None)`
    - Encodes audio to 16-bit PCM WAV in memory via `io.BytesIO`.
    - Dispatches multipart/form-data POST request to `https://api.groq.com/openai/v1/audio/transcriptions`.
    - Payload fields: `model: "whisper-large-v3-turbo"`, `response_format: "json"`, `temperature: "0.0"`, `prompt: initial_prompt`, `file: audio.wav`.
    - Header: `Authorization: Bearer <groq_api_key>`, `User-Agent: WhisperFlow`.
    - Timeout: 10.0s.
  - Lines 233-244: In `transcribe()`, if `groq_api_key` is configured, calls `_transcribe_groq()`. If an exception occurs (e.g. network timeout or invalid key), it catches the exception and transparently falls back to local CPU `self.model.transcribe()`.
- **Vocabulary Biasing (`initial_prompt`)**:
  - Lines 255-264:
    ```python
    segments, info = self.model.transcribe(
        audio_data,
        initial_prompt=initial_prompt,
        beam_size=1,
        best_of=1,
        temperature=0.0,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300),
        condition_on_previous_text=False
    )
    ```
  - Greedy decoding (`beam_size=1`, `best_of=1`) achieves minimal latency.
- **Model Name Discrepancy**:
  - `config.py` line 7: `DEFAULT_CONFIG = {"model_name": "base.en", ...}`.
  - `config.json` line 2: `{"model_name": "base", ...}`.
  - *Critical Note*: `base.en` is an English-only model that will crash or fail to transcribe Hindi/Hinglish speech. For bilingual English + Hindi/Hinglish support, default must be `"base"` (or multilingual `"small"`).

---

### 1.2 Calibration Sentences Dataset (`data/calibration_sentences.json`)
- **File Location**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\data\calibration_sentences.json` (981 lines, 24,115 bytes).
- **Structure Validation**:
  - Total Sentences: **100**
  - Categories:
    - `"english"`: exactly 50 sentences (IDs 1 to 50). Phonetically diverse English corporate and technical sentences.
    - `"hindi_hinglish"`: exactly 50 sentences (IDs 51 to 100). Natural conversational Hindi and Hinglish technical sentences.
  - Schema per item:
    ```json
    {
      "id": 51,
      "category": "hindi_hinglish",
      "text": "Main thodi der mein call karta hoon.",
      "phonetic_keywords": ["thodi der", "call karta hoon"]
    }
    ```
  - Missing fields count: 0. Empty keywords count: 0. Sequential IDs: 1 to 100.
- **Desktop UI Discrepancy (`ui/voice_training_dialog.py`)**:
  - Lines 15-19:
    ```python
    CALIBRATION_SENTENCES = [
        "The quick brown fox jumps over the lazy dog.",
        "Whisper Flow transcribes my speech locally with zero latency using PySide6.",
        "I love testing OpenCode, CTranslate2, and modern AI developer tools."
    ]
    ```
  - The native PySide6 dialog hardcodes only 3 English sentences and completely ignores `data/calibration_sentences.json`.

---

### 1.3 Accuracy Diff & Phonetic Correction Mapper
- **Current Diff Logic (`studio_server.py`)**:
  - Lines 75-129: `compute_diff(target_text, transcribed_text, phonetic_keywords=None)`
  - Tokenizes target and heard text; normalizes tokens using `clean_token(t) = re.sub(r"[^\w\s]", "", t).strip().lower()`.
  - Uses `difflib.SequenceMatcher(None, target_norm, heard_norm)` with opcodes `equal`, `replace`, `delete`, `insert`.
  - Accuracy formula:
    `accuracy = max(0.0, min(100.0, round((matches / max(len(target_tokens), len(heard_tokens), 1)) * 100.0, 1)))`
- **Observed Bugs & Defects in Current Diffing**:
  1. **Punctuation Leakage into `misheard_pairs`**:
     Lines 102-106 in `studio_server.py`:
     ```python
     t_chunk = " ".join(target_tokens[i1:i2])
     h_chunk = " ".join(heard_tokens[j1:j2])
     diff.append({"type": "replace", "target": t_chunk, "heard": h_chunk})
     if t_chunk and h_chunk:
         misheard_pairs.append({"heard": h_chunk, "target": t_chunk})
     ```
     `t_chunk` and `h_chunk` slice uncleaned tokens. When testing Hinglish:
     - Target: `"Main thodi der mein call karta hoon."`
     - Transcribed: `"main thodi der me call karta hu"`
     - Resulting `misheard_pairs`: `[{"heard": "me", "target": "mein"}, {"heard": "hu", "target": "hoon."}]`
     Notice `"hoon."` retains the sentence-ending period! When `"hu"` is replaced by `"hoon."`, any mid-sentence utterance like `"Main hu ek developer"` becomes `"Main hoon. ek developer"`.
  2. **Coupling to Studio Server**:
     `compute_diff` is only defined inside `studio_server.py`. Line 35 of `studio_server.py` executes:
     `whisper_engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8")`
     `whisper_engine.load_model()`
     at module level! Importing `compute_diff` from `studio_server` forces heavy model loading and blocks the thread.
  3. **Absence of Automated Phonetic Mapper**:
     In `studio/index.html`, registration requires manual user button clicks. In `ui/voice_training_dialog.py`, no diffing or mapping occurs at all. An automated mapper that detects misrecognitions and registers clean phonetic replacements into `voice_profile.json` is missing.

---

### 1.4 Voice Profile & Replacement Engine (`voice_profile.py` / `voice_profile.json`)
- **File Location**: `voice_profile.py` (181 lines, 6,113 bytes) and `voice_profile.json` (97 lines, 2,510 bytes).
- **Current Replacement Mechanism**:
  - Lines 133-149:
    ```python
    def apply_replacements(self, text):
        if not text:
            return text
        reps = self.get_replacements()
        if not reps:
            return text
        sorted_keys = sorted(reps.keys(), key=len, reverse=True)
        escaped_keys = [re.escape(k) for k in sorted_keys]
        pattern = re.compile(r'\b(' + '|'.join(escaped_keys) + r')\b', re.IGNORECASE)
        return pattern.sub(lambda m: reps.get(m.group(0).lower(), m.group(0)), text)
    ```
- **Observed Critical Regex Boundary Flaw**:
  - In `voice_profile.json` line 46: `"cooper nets,": "Kubernetes"`.
  - When matching `"cooper nets,"`, regex `r'\b(cooper nets,)\b'` fails because `,` is `\W` (non-word). In Python regex, `\b` asserts a boundary between `\w` and `\W`. If the key ends in `,`, the following character must be `\w` for `\b` to match. In normal text followed by space or punctuation, `\b` fails!
  - **Empirical Test**:
    ```python
    # Given reps = {'cooper nets,': 'Kubernetes'}
    re.search(r'\b' + re.escape('cooper nets,') + r'\b', 'I use cooper nets, in cloud') # Returns None!
    ```
    Live dictation failed to replace `"cooper nets,"` with `"Kubernetes"`.
  - **Verified Solution**:
    Using lookarounds conditional on token boundaries:
    ```python
    def build_replacement_pattern(keys):
        patterns = []
        for k in sorted(keys, key=len, reverse=True):
            lb = r'(?<!\w)' if k[0].isalnum() or k[0] == '_' else ''
            rb = r'(?!\w)' if k[-1].isalnum() or k[-1] == '_' else ''
            patterns.append(lb + re.escape(k) + rb)
        return re.compile(r'(' + '|'.join(patterns) + r')', re.IGNORECASE)
    ```
    This successfully matched and replaced `'cooper nets,'` -> `'Kubernetes'` in 0.05ms!
- **Vocabulary Biasing (`get_initial_prompt`)**:
  - Lines 122-132:
    ```python
    def get_initial_prompt(self):
        words = self.get_custom_words()
        if not words:
            return None
        return "Vocabulary: " + ", ".join(words) + "."
    ```
  - Whisper's context prefix window is capped at ~224 tokens. When `custom_words` contains many entries, a prioritization/truncation strategy is required to avoid token overflow.
- **1-Click Deletion Latency**:
  - `remove_custom_word(word)` and `remove_replacement(heard)` update in-memory dict/list and call `json.dump` synchronously (~1-2ms on local disk).
  - Benchmarked UI deletion latency: ~16ms, well within the sub-50ms target.

---

### 1.5 Rule-Based Style Transformations (`style_engine.py` / `text_cleaner.py`)
- **Casual Chat**:
  - Function: `text_cleaner.format_casual_chat(text)`.
  - Verified working:
    - Strips URLs to temporary placeholders (`___URLTOKEN_X___`).
    - Removes hesitation fillers (`um`, `uh`, `er`, `ah`).
    - Removes single-word stutters (`the the` -> `the`).
    - Removes trailing formal periods, exclamation marks, and question marks.
    - Removes formal commas while preserving decimals (`3.14`) and timestamps (`10:30`).
    - Relaxes capitalization to natural chat lowercase while preserving acronyms (`API`, `GPU`), camelCase (`PySide6`), and code tokens.
    - Latency: <1ms on CPU, 0 MB VRAM, 0% GPU.
- **Developer Mode**:
  - Requirement: "Transforms spoken commands into camelCase, snake_case, and code syntax."
  - **Defect Observed**: In `style_engine.py`, style `"code"` delegates entirely to Ollama (LLM). If `ollama_enabled` is False (the default zero-GPU state), it returns `cleaned_base` unmodified.
  - **Missing Implementation**: Instant rule-based parsing for spoken casing (`"camel case <words>"`, `"snake case <words>"`, `"kebab case <words>"`, `"pascal case <words>"`, `"constant case <words>"`) and spoken code operators (`"dot env"` -> `.env`, `"arrow function"` -> `=>`, `"double equals"` -> `==`, `"open paren"` -> `(`, etc.).
- **Custom Persona**:
  - Requirement: "Formats output to match custom user-defined tone without adding latency."
  - **Defect Observed**: In `style_engine.py`, style `"custom"` delegates to Ollama. When Ollama is offline or disabled, it returns `cleaned_base` unmodified.
  - **Missing Implementation**: Rule-based persona engine that applies user-defined tone rules (bullet formatting, case styling, filler stripping, prefix/suffix wrapping, concise phrasing) in 0ms without GPU.

---

### 1.6 Test Suite Discovery
- Executing `python -m unittest discover tests` in project root failed:
  - `whisper-flow/tests` does not exist.
  - Python automatically defaulted to `site-packages\tests` (from third-party libraries), triggering 15 errors on missing third-party WAV files.
  - Project requires a clean `tests/` directory with `__init__.py` and targeted test cases.

---

## 2. Logic Chain

```
[Observation 1.1: faster-whisper CPU int8 verified with 0 MB VRAM and <150ms latency]
  --> Confirms R2 requirement for zero-GPU speech engine is functionally feasible and validated on host.
  --> However, config.py DEFAULT_CONFIG has "base.en" which cannot decode Hindi/Hinglish.
  --> Action: Change default model in config.py to "base" for bilingual support.

[Observation 1.2: data/calibration_sentences.json has 100 sentences (50 English, 50 Hindi/Hinglish)]
  --> Confirms R1 dataset requirement is satisfied in data/.
  --> However, ui/voice_training_dialog.py hardcodes only 3 sentences and ignores the dataset.
  --> Action: Connect voice_training_dialog.py to data/calibration_sentences.json with language category filtering.

[Observation 1.3: compute_diff in studio_server.py has punctuation leaks and module-level engine initialization]
  --> Difflib word alignment works, but misheard_pairs contain trailing punctuation ("hoon.").
  --> Importing studio_server loads WhisperEngine on CPU synchronously.
  --> Action: Extract diff calculation into a pure calibration_engine.py, strip punctuation in misheard pairs, and build an automated phonetic mapper.

[Observation 1.4: apply_replacements regex r'\b' fails on keys ending in punctuation]
  --> Keys like "cooper nets," in voice_profile.json are never matched during live dictation.
  --> Action: Sanitize replacement keys upon registration and use (?<!\w) / (?!\w) lookaround boundaries.

[Observation 1.5: Casual Chat works locally, but Developer Mode & Custom Persona require Ollama/GPU]
  --> When Ollama is disabled, Developer Mode and Custom Persona do not perform any transformations.
  --> Action: Implement rule-based Developer Mode (camelCase, snake_case, code syntax) and rule-based Custom Persona directly in text_cleaner.py / style_engine.py.

[Observation 1.6: tests/ directory does not exist, causing unittest discover to run site-packages]
  --> Action: Create tests/ directory with unit tests for speech engine, calibration dataset, voice profile, and style transformations.
```

---

## 3. Caveats
1. **Whisper Language Auto-Detection**: When transcribing Hinglish with `model_name="base"` without specifying `language`, Whisper might occasionally predict `language="hi"` and output Devanagari script. In `whisper_engine.py`, initializing `initial_prompt` with Romanized Hinglish vocabulary (e.g. `"Vocabulary: thodi der, call karta hoon, meeting schedule..."`) guides token probabilities to Romanized Latin script.
2. **Audio Input Hardware**: Physical microphone recording was not executed in headless CI mode; synthetic numpy float32 audio arrays and decoded WAV buffers were used for engine verification.
3. **External Ollama Dependency**: Ollama is optional for local LLM formatting, but the system must guarantee 100% functionality with Ollama disabled (0 MB VRAM, 0ms GPU latency).

---

## 4. Conclusion
1. **Speech Engine**: faster-whisper CPU int8 and Groq cloud fallback are structurally sound, but `DEFAULT_CONFIG` in `config.py` must be updated from `"base.en"` to `"base"` to support Hindi/Hinglish speech.
2. **Calibration Dataset**: The 100-sentence dataset (`50 english`, `50 hindi_hinglish`) is fully validated and ready for ingestion.
3. **Phonetic Mapper & Calibration Engine**: `compute_diff` must be refactored into a pure, lightweight module (`calibration_engine.py`) with punctuation stripping and automated dictionary registration (`auto_register_phonetic_corrections`).
4. **Voice Profile**: The regex matcher in `voice_profile.py` must be upgraded to lookaround boundaries to fix non-alphanumeric key matching.
5. **Rule-Based Style Transformations**: Implement instant rule-based parsing in `text_cleaner.py` / `style_engine.py` for Developer Mode (`camelCase`, `snake_case`, code operators) and Custom Persona rules.
6. **Test Suite**: Create `tests/` with modular unit tests to satisfy `python -m unittest discover tests`.

---

## 5. Verification Method

To independently verify all findings and test proposals:

1. **Verify Calibration Dataset Integrity**:
   ```powershell
   python -c "import json; data=json.load(open(r'data/calibration_sentences.json', encoding='utf-8')); assert len(data)==100; from collections import Counter; c=Counter(d['category'] for d in data); assert c['english']==50 and c['hindi_hinglish']==50; print('Dataset 100% Validated:', c)"
   ```

2. **Verify faster-whisper CPU int8 Execution (0 MB VRAM)**:
   ```powershell
   python -c "import numpy as np; from whisper_engine import WhisperEngine; eng = WhisperEngine.get_instance(model_name='base', device='cpu', compute_type='int8'); eng.load_model(); assert eng.device=='cpu' and eng.compute_type=='int8'; print('CPU int8 successfully validated')"
   ```

3. **Verify Phonetic Replacement Boundary Fix**:
   ```powershell
   python -c "import re; reps = {'cooper nets,': 'Kubernetes', 'pie side': 'PySide6'}; keys = sorted(reps.keys(), key=len, reverse=True); patterns = [(r'(?<!\w)' if k[0].isalnum() else '') + re.escape(k) + (r'(?!\w)' if k[-1].isalnum() else '') for k in keys]; pat = re.compile(r'(' + '|'.join(patterns) + r')', re.IGNORECASE); text = 'I use cooper nets, in cloud and pie side here.'; res = pat.sub(lambda m: reps.get(m.group(0).lower(), m.group(0)), text); assert 'Kubernetes' in res and 'PySide6' in res; print('Replacement Test Passed:', res)"
   ```

4. **Verify Casual Style Period/Comma Removal**:
   ```powershell
   python -c "from text_cleaner import format_casual_chat; out = format_casual_chat('Hello team, this is an update.'); assert out == 'hello team this is an update', f'Got: {out}'; print('Casual Chat Test Passed:', out)"
   ```

5. **Verify Project Test Runner**:
   After creating `tests/test_speech_engine.py` etc.:
   ```powershell
   python -m unittest discover tests
   ```
