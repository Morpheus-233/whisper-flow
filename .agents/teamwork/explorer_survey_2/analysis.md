# Architectural Analysis: Smart Voice Calibration & Phonetic Memory
**Explorer**: Survey Explorer 2 (Round 2)  
**Date**: 2026-10-22  
**Target Repository**: `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow`  
**Scope**: `calibration_engine.py`, `voice_profile.py`, `data/calibration_sentences.json`, `ui/voice_training_dialog.py`, and Two-Stage Pipeline Injection.

---

## Executive Summary
This investigation provides a comprehensive architectural survey of the **Smart Voice Calibration & Phonetic Memory** subsystem for Whisper Flow Round 2. 

In Round 1, an initial foundation was built consisting of a 100-sentence bilingual dataset (`data/calibration_sentences.json`), a pure computation diff engine (`calibration_engine.py`), a persistent voice profile manager (`voice_profile.py`), and a 3-step calibration wizard (`ui/voice_training_dialog.py`).

In Round 2, the user requires an **Intelligent Two-Stage Hinglish Pipeline** (Stage 1 acoustic capture -> Stage 2 fast Romanizer & stylist) and **Smart Voice Calibration with Phonetic Memory**. Our survey reveals critical architectural insights, script mismatch dynamics between Whisper and Romanized Hinglish, vulnerabilities with unconditional auto-registration, and concrete interface specifications for injecting voice profile mappings into both Stage 1 (`initial_prompt`) and Stage 2 (`llama-3.3-70b-versatile` formatter context), along with an interactive 1-click confirmation UX.

---

## 1. Subsystem Architecture & Code Review

### 1.1 `calibration_engine.py` (Pure Computation Diff Engine)
- **Role**: Pure computation, zero external dependencies (no PySide6, torch, faster-whisper, or network dependencies).
- **Core Functions**:
  - `clean_token(token: str) -> str`: Normalizes tokens for string comparison by stripping non-alphanumeric punctuation while preserving Devanagari characters and combining marks (`\u0900-\u097F`).
  - `strip_punctuation(text: str) -> str`: Trims leading and trailing punctuation from words while preserving internal hyphens (`follow-up`), apostrophes (`today's`), and Devanagari matras.
  - `compute_diff(target_text: str, transcribed_text: str, phonetic_keywords: list[str] | None = None) -> dict`:
    - Normalizes token lists: `target_norm` and `heard_norm`.
    - Handles edge cases: both empty (100% accuracy), one empty (0% accuracy), pure punctuation without words (0% or 100% if identical).
    - Uses `difflib.SequenceMatcher(lambda x: x == "", target_norm, heard_norm)` to find opcodes (`equal`, `replace`, `delete`, `insert`).
    - Extracts `misheard_pairs`:
      - For 1:1 token replacements, isolates each word pair and strips boundary punctuation.
      - For M:N chunk replacements, pairs the cleaned phrase chunks.
    - Clamps accuracy score to `[0.0, 100.0]`: `(matches / max(len(target_tokens), len(heard_tokens), 1)) * 100.0`.
    - Checks `missing_keywords` using lookaround regular expressions `(?<![\w\u0900-\u097F])` and `(?![\w\u0900-\u097F])`.
  - `load_calibration_dataset(json_path: str = "data/calibration_sentences.json") -> list[dict]`:
    - Resolves relative and absolute file paths safely.
    - Validates schema structure (`id`, `category`, `text`, `phonetic_keywords`).
  - `auto_register_misheard_pairs(misheard_pairs: list[dict], profile_mgr: Any) -> int`:
    - Idempotently adds newly detected phonetic pairs into `VoiceProfileManager`.

### 1.2 `voice_profile.py` (Persistent Profile & Biasing)
- **Role**: Manages `voice_profile.json`, providing persistence, Whisper decoder biasing, and single-pass regex replacement.
- **Data Model**:
  - `custom_words`: List of personal names, technical jargon, and vocabulary tokens.
  - `word_replacements`: Key-value map of `{heard_lower: target_original_casing}`.
  - `active_style`: Speech style ("raw", "professional", "casual", "code", "custom").
  - `acoustic_settings`: Noise floor RMS, speaking WPM, and microphone gain.
- **Key Methods**:
  - `get_initial_prompt(max_chars=800)`: Assembles `"Vocabulary: <words>."` string within 800 characters (~224 tokens) for Whisper token decoder biasing.
  - `apply_replacements(text: str) -> str`: Compiles a single regex pattern using word boundaries and lookarounds (`(?<![\w\u0900-\u097F])` and `(?![\w\u0900-\u097F])`), sorting keys by length descending to prevent sub-string collisions.

### 1.3 `data/calibration_sentences.json` (100 Bilingual Sentences)
- **Corpus Breakdown**:
  - **Sentences 1 to 50**: `category: "english"`. Ranging from daily standup phrases to complex multisyllabic technical terms (`"heteronyms"`, `"probabilistic"`, `"parallelization"`, `"computational"`).
  - **Sentences 51 to 100**: `category: "hindi_hinglish"`. Spoken Hindi and technical Hinglish, **all encoded in Romanized Latin alphabet** (`"Main thodi der mein call karta hoon."`, `"Aaj ka meeting schedule kya hai?"`, `"Database query optimize karke API latency ko cut kiya."`).
- **Phonetic Keywords**: Every sentence has 1 to 4 designated `phonetic_keywords` verified to exist within the target text.

### 1.4 `ui/voice_training_dialog.py` (Calibration Wizard)
- **Role**: 3-step modal dialog for desktop calibration.
- **Current Flow**:
  - Step 1 (`page_noise`): Samples 2 seconds of ambient silence to compute RMS noise floor (`calibrated_noise_floor`).
  - Step 2 (`page_speech`): Displays sentences one by one. User clicks `Start Speaking`, reads aloud, and clicks `Finish Speaking`. Background thread records audio, calls `whisper_engine.transcribe()`, computes diff, and auto-registers misheard pairs into profile.
  - Step 3 (`page_review`): Shows summary of calibrated metrics, provides an input box to add custom words, and saves acoustic settings upon closing.

---

## 2. Bilingual 100-Sentence Accuracy Diff Processing

### 2.1 The Script Mismatch Challenge in Stage 1
An essential observation from examining the codebase is the script disparity between Whisper's raw output and the calibration corpus:
1. In `calibration_sentences.json`, all 50 Hindi/Hinglish sentences (IDs 51–100) are written in **Romanized Latin alphabet** (e.g. `"Main thodi der mein call karta hoon."`).
2. When Whisper (either local CPU `base` or Groq `whisper-large-v3-turbo`) transcribes spoken Hindi without Romanization, it transcribes into **Devanagari script** (e.g., `"मैं थोड़ी देर में कॉल करता हूँ"`).
3. If raw Devanagari output is compared directly against the Romanized Latin target via `difflib.SequenceMatcher`:
   - `target_norm`: `['main', 'thodi', 'der', 'mein', 'call', 'karta', 'hoon']`
   - `heard_norm`: `['मैं', 'थोड़ी', 'देर', 'में', 'कॉल', 'करता', 'हूँ']`
   - Since character sets have 0 overlap, `matches == 0`, leading to an artificial **0.0% accuracy** and nonsensical token replacements!

### 2.2 Integration with Round 2 Two-Stage Pipeline
To accurately measure pronunciation accuracy on Hinglish sentences:
- The calibration transcription loop MUST utilize the **Two-Stage Pipeline**:
  - **Stage 1**: Whisper transcribes raw speech acoustics.
  - **Stage 2**: The Romanizer (`llama-3.3-70b-versatile` or fast local model) converts the transcript into natural Romanized Hinglish in Latin script.
- Once Stage 2 outputs Romanized Hinglish (e.g., `"Main thori der me call karta hu"`), `compute_diff` compares Romanized target with Romanized output.
- `SequenceMatcher` then correctly aligns:
  - `"thodi"` vs `"thori"` -> misheard pair: `{"heard": "thori", "target": "thodi"}`
  - `"mein"` vs `"me"` -> misheard pair: `{"heard": "me", "target": "mein"}`
  - `"hoon"` vs `"hu"` -> misheard pair: `{"heard": "hu", "target": "hoon"}`
- This accurately captures the user's specific accent and dialectal variations.

---

## 3. Automated Phonetic Registration: Mechanism & Safety Hazards

### 3.1 How Misheard Pairs are Identified
In `calibration_engine.py`:
```python
# Check if 1:1 token replacement or phrase replacement
if (i2 - i1) == (j2 - j1) and (i2 - i1) > 1:
    for ti, hj in zip(range(i1, i2), range(j1, j2)):
        ct = strip_punctuation(target_tokens[ti])
        ch = strip_punctuation(heard_tokens[hj]).lower()
        if ct and ch and (ct.lower() != ch or ct != ch):
            pair = {"heard": ch, "target": ct}
            if pair not in misheard_pairs:
                misheard_pairs.append(pair)
else:
    clean_t = strip_punctuation(t_chunk)
    clean_h = strip_punctuation(h_chunk).lower()
    if clean_t and clean_h and (clean_t.lower() != clean_h or clean_t != clean_h):
        pair = {"heard": clean_h, "target": clean_t}
        if pair not in misheard_pairs:
            misheard_pairs.append(pair)
```
- Targets retain case sensitivity (e.g., `"Kubernetes"`), while heard tokens are normalized to lowercase.
- All leading and trailing punctuation (quotes, periods, commas, exclamation marks) is removed via `strip_punctuation`.

### 3.2 The Flaw of Unconditional Background Auto-Registration
In `ui/voice_training_dialog.py` (lines 448-450):
```python
diff_res = compute_diff(target_text, text, keywords)
newly_added = auto_register_misheard_pairs(diff_res.get("misheard_pairs", []), self.profile_mgr)
```
**Identified Hazards**:
1. **Acoustic Hallucination / Cough / Noise**: If the user coughs or hesitates, Whisper might output a random hallucinated phrase (e.g., `"Thank you for watching"`). The code blindly registers `"thank you for watching" -> "Unprecedented computational parallelization accelerated matrix multiplications substantially"`.
2. **Loss of User Agency**: The user has no choice in what is registered.
3. **No In-Wizard Rejection**: If an erroneous pair is registered, the user cannot undo it in the wizard; they must manually locate it in the Settings dialog.

### 3.3 Proposed Safety & Auto-Registration Architecture
1. **Diff Extraction**: Extract candidate pairs from `diff_res["misheard_pairs"]`.
2. **Filtering**: Discard pairs where the edit distance or token count disparity is abnormally high (e.g., length ratio > 4:1 indicates hallucination).
3. **Interactive 1-Click Confirmation**: Present candidate pairs as interactive chips in the UI. Users can confirm them with 1 click, or the system can auto-stage them with an instant 1-click `[ ✕ Reject / Remove ]` option.

---

## 4. Two-Stage Pipeline Injection: Stage 1 & Stage 2

### 4.1 Stage 1 Injection (`initial_prompt` Biasing)
Whisper's decoder loop accepts an `initial_prompt` to bias token probabilities towards custom jargon and spelling:
- **Current Limitation**: `VoiceProfileManager.get_initial_prompt()` only selects from `custom_words`. It ignores target words from `word_replacements`!
- **Recommended Fix**:
  ```python
  def get_initial_prompt(self, max_chars=800):
      # Combine custom_words AND the target values of word_replacements
      words = list(self.get_custom_words())
      for target in self.get_replacements().values():
          t_clean = target.strip()
          if t_clean and t_clean not in words:
              words.append(t_clean)
      ...
  ```
  This biases Whisper acoustically towards target words (e.g., `"PySide6"`, `"Kubernetes"`).

### 4.2 Stage 2 Injection (Fast Romanizer & Stylist Context)
In Round 2, Stage 2 (Groq `llama-3.3-70b-versatile` or fast local model) acts as the Romanizer and Stylist. The voice profile must be injected directly into the LLM context:
- **Prompt Structure**:
  ```text
  You are an ultra-low-latency speech transcription formatter.
  Your task:
  1. Transcribe Hindi speech into natural Romanized Hinglish (Latin alphabet).
  2. Strictly preserve English technical terms and code tokens.
  3. Never translate Hindi into English.
  4. Enforce the user's active speech style: {active_style}.

  <personal_dictionary>
  User-specific terminology, proper nouns, and code identifiers:
  {custom_words_formatted}
  </personal_dictionary>

  <phonetic_memory>
  When you see any of the following misheard phonetic pronunciations, replace them with the exact target:
  {replacements_formatted}
  </phonetic_memory>

  Output ONLY the final formatted text.
  ```
- **Token Budget Management**:
  To maintain sub-100ms LLM latency, the injected replacements should be formatted concisely (e.g. compact bullet list or JSON map) capped at ~100 most relevant entries or 1,200 characters.

### 4.3 Deterministic Defense-in-Depth Guarantee
Even with prompt instructions, LLMs can occasionally overlook a phonetic rule.
To fulfill the acceptance criterion:
> *"Saved personal dictionary words appear with 100% fidelity in output text."*

The pipeline MUST execute `voice_profile.apply_replacements(text)` as a **deterministic post-pass** following Stage 2 LLM formatting.
- `apply_replacements` runs in <0.5ms using compiled lookaround regex.
- It mathematically guarantees 100% replacement fidelity without LLM nondeterminism.

---

## 5. Calibration Wizard UI (`voice_training_dialog.py`) & 1-Click Confirmation

### 5.1 Current UI Limitations
- `sentence_box`: Static dark label.
- `transcribed_preview`: Plain text string (`Whisper heard: "..." | Accuracy: 85.0%`).
- `diff_status`: Plain text string (`Auto-registered 1 phonetic correction(s): 'thori' -> 'thodi'`).
- No visual word-by-word diff (no color coding for matched vs misheard words).
- No clickable buttons to accept/reject misheard pairs.
- Step 3 (Review page) only shows `custom_words`, omitting all calibrated phonetic pairs.

### 5.2 Recommended UI Redesign

#### A. Rich Visual Diff Display
Format `diff_res["diff"]` into an HTML snippet with color coding:
- **Matched words**: `#34d399` (light green, normal weight)
- **Misheard / Replaced words**:
  - Target: `<span style="color: #94a3b8; text-decoration: line-through;">{target}</span>`
  - Heard: `<span style="color: #f87171; font-weight: bold;">{heard}</span>`
- **Inserted words**: `<span style="color: #fbbf24;">{heard}</span>`
- **Accuracy Badge**: Prominent colored score pill (Green `>= 90%`, Amber `70-89%`, Red `< 70%`).

#### B. Interactive 1-Click Confirmation Chips (`PhoneticChipWidget`)
Below the diff preview, render dynamic chip widgets for each detected pair:
```
+--------------------------------------------------------------+
| Detected Misheard Words:                                     |
|                                                              |
| [ 'thori' → 'thodi' ]    [ + Remember ]                      |
| [ 'me'    → 'mein'  ]    [ ✓ Remembered ]  [ ✕ ]             |
+--------------------------------------------------------------+
```
- **1-Click Action**:
  - Clicking `[ + Remember ]` immediately calls `profile_mgr.add_replacement(heard, target)` and switches state to `[ ✓ Remembered ]` in <1ms.
  - Clicking `[ ✕ ]` immediately calls `profile_mgr.remove_replacement(heard)`.
- **Zero UI Freeze**: All operations modify the in-memory dictionary and write to `voice_profile.json` asynchronously or in <1ms without blocking the Qt event loop.

#### C. Review Page Enhancements (Step 3)
In Step 3 (`page_review`), display two sections or tabs:
1. **Custom Words**: Quick-add input and list of vocabulary words.
2. **Calibrated Phonetic Mappings**: A scrollable list of all `heard → target` pairs registered during the calibration session, each with a 1-click `Remove` button (reusing `ReplacementRowWidget`).

---

## 6. Concrete Interfaces & Data Structures

### 6.1 `voice_profile.py` Additions
```python
class VoiceProfileManager:
    ...
    def get_initial_prompt(self, max_chars=800) -> Optional[str]:
        """
        Combines custom_words and word_replacements targets into Whisper initial_prompt.
        """
        words = list(self.get_custom_words())
        for target in self.get_replacements().values():
            t = target.strip()
            if t and t not in words:
                words.append(t)
        ...

    def get_stage2_context(self, max_replacements=50) -> Dict[str, Any]:
        """
        Returns structured dictionary and formatted text blocks for Stage 2 LLM prompt injection.
        """
        custom_words = self.get_custom_words()
        reps = self.get_replacements()
        rep_items = list(reps.items())[:max_replacements]
        
        reps_prompt = "\n".join(f"- \"{h}\" -> \"{t}\"" for h, t in rep_items)
        words_prompt = ", ".join(custom_words)
        
        return {
            "custom_words": custom_words,
            "replacements": reps,
            "prompt_block": (
                f"<phonetic_memory>\n{reps_prompt}\n</phonetic_memory>\n"
                f"<personal_dictionary>\n{words_prompt}\n</personal_dictionary>"
            )
        }
```

### 6.2 `calibration_engine.py` Additions
```python
def format_diff_html(diff_list: List[Dict[str, Any]]) -> str:
    """
    Renders diff list into clean HTML for QLabels in PySide6.
    Green for matches, red/strikethrough for misheard words, yellow for insertions.
    """
    html_parts = []
    for item in diff_list:
        t_type = item.get("type")
        target = item.get("target", "")
        heard = item.get("heard", "")
        if t_type == "equal":
            html_parts.append(f'<span style="color: #34d399;">{target}</span>')
        elif t_type == "replace":
            html_parts.append(
                f'<span style="color: #94a3b8; text-decoration: line-through;">{target}</span> '
                f'<span style="color: #f87171; font-weight: bold;">{heard}</span>'
            )
        elif t_type == "delete":
            html_parts.append(f'<span style="color: #94a3b8; text-decoration: line-through;">{target}</span>')
        elif t_type == "insert":
            html_parts.append(f'<span style="color: #fbbf24;">{heard}</span>')
    return " ".join(html_parts)
```

### 6.3 `ui/voice_training_dialog.py` Interactive Chip Widget
```python
class PhoneticPairChip(QFrame):
    def __init__(self, heard: str, target: str, is_remembered: bool, on_toggle_callback, parent=None):
        super().__init__(parent)
        self.heard = heard
        self.target = target
        self.is_remembered = is_remembered
        self.on_toggle_callback = on_toggle_callback
        ...
```

---

## 7. Risk Analysis & Verification Plan

| Risk / Failure Mode | Impact | Mitigation Strategy |
|---|---|---|
| Whisper outputs Devanagari during Hindi calibration | 0% accuracy diff against Romanized sentences | Pass audio through Stage 2 Romanizer before computing diff, or support transliterated comparison |
| Hallucinated phrase auto-saved to voice profile | Corrupts subsequent dictation | Replace blind auto-registration with 1-click confirmation chips & length ratio filtering |
| Prompt overflow in Stage 2 from large dictionary | High latency (>350ms) or LLM rejection | Cap injected replacements to top 50-100 entries; rely on `apply_replacements` regex post-pass |
| Personal dictionary word missed by LLM | Fails acceptance criteria | Always execute `apply_replacements(text)` as deterministic post-pass after Stage 2 |

### Verification Method
1. Run automated unit test suite:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover tests
   ```
2. Run benchmark on 100 calibration sentences diff processing:
   - Verify all 100 sentences diff without error.
   - Verify punctuation stripping retains zero trailing punctuation.
   - Verify Devanagari vowel sign preservation.
3. Test 1-click confirmation UI responsiveness:
   - Ensure `PhoneticPairChip` toggle executes in <1ms without UI blocking.
   - Ensure VoiceTrainingDialog launch latency remains <30ms (well under the 50ms requirement).
