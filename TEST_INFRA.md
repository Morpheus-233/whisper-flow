# TEST_INFRA: Testing Infrastructure & Methodology Specification
## Whisper Flow Round 2 — Intelligent Two-Stage Hinglish Pipeline & Desktop Hardening

---

## 1. Testing Philosophy & Architecture

The testing infrastructure for Whisper Flow Round 2 enforces **requirement-driven, opaque-box, and progressive verification**. Tests treat components as black boxes adhering strictly to the interface contracts and requirements defined in `ORIGINAL_REQUEST.md` (specifically `## 2026-10-22T09:54:41Z`) and `PROJECT.md`.

### Core Quality Pillars:
1. **Opaque-Box Verification**: Test observable behavior, input-output transformations, signal contracts, and latency budgets rather than internal private variables.
2. **Progressive Testability**: Each test module is self-contained and independently executable. Features can be verified in isolation with appropriate test doubles for external I/O (Groq API network requests, sound device drivers).
3. **Zero Cheating & Forensic Integrity**: No facade tests, no hardcoded synthetic passes, and no test-only branching. All benchmark tests exercise genuine transformation and diff logic.
4. **Sub-millisecond Deterministic Benchmarking**: Latency budgets are asserted using high-resolution monotonic clocks (`time.perf_counter()`).

---

## 2. Test Design Methodologies

### 2.1 Category-Partition Method

We decompose the Round 2 system into functional parameters, categories, and partitions:

| Component | Category / Parameter | Partitions & Choices |
|-----------|----------------------|----------------------|
| **Stage 1: Acoustic Capture** | Engine Selection | `[P1] Groq Cloud (whisper-large-v3-turbo)`<br>`[P2] Local CPU (faster-whisper base int8)` |
| | Spoken Language Input | `[P3] Devanagari Hindi (native audio)`<br>`[P4] Mixed Hinglish (code tokens + Hindi)`<br>`[P5] Clean English`<br>`[P6] Empty audio (0 samples)`<br>`[P7] Clipped audio (> 1.0 amplitude)` |
| | Whisper Decoding Task | `[P8] task="transcribe" (Strict: No forced translation)`<br>`[P9] task="translate" (Forbidden/Invalid in pipeline)` |
| | Context Biasing | `[P10] No initial prompt`<br>`[P11] Vocabulary prompt with custom words`<br>`[P12] Large vocabulary prompt exceeding 800-char context window` |
| **Stage 2: Fast Romanizer & Stylist** | Input Script | `[P13] Devanagari Hindi script`<br>`[P14] Mixed Devanagari + Latin technical tokens`<br>`[P15] Already Romanized Hinglish`<br>`[P16] English text` |
| | Romanization Target | `[P17] Natural Romanized Hinglish in Latin alphabet`<br>`[P18] English translation (Strictly Forbidden: Error if detected)`<br>`[P19] Devanagari preservation (Forbidden in final output)` |
| | Technical Term Preservation | `[P20] Technical keywords: "deploy", "server", "github", "commit", "PR", "database", "python"` |
| | Active Style Preset | `[P21] Casual Chat (strip trailing periods/commas, relaxed case)`<br>`[P22] Developer Mode (camelCase, snake_case, code syntax)`<br>`[P23] Professional (well-punctuated prose)`<br>`[P24] Custom Persona (user rules)`<br>`[P25] Raw (unmodified)` |
| | Processing Engine | `[P26] Groq Cloud (llama-3.3-70b-versatile)`<br>`[P27] Local Fast Romanizer (<0.01ms deterministic)` |
| **Phonetic Memory & Calibration** | Dataset Input | `[P28] 50 English calibration sentences`<br>`[P29] 50 Hindi/Hinglish Romanized sentences` |
| | Diff Sequence Matching | `[P30] Perfect match (100.0% accuracy)`<br>`[P31] Partial pronunciation variance (e.g. 'thori' vs 'thodi')`<br>`[P32] Complete mismatch (0.0% accuracy)`<br>`[P33] Pure punctuation input` |
| | Confirmation & Memory | `[P34] 1-Click Interactive Confirmation Chip`<br>`[P35] User Rejection / Dismissal`<br>`[P36] Dual Injection: Stage 1 initial_prompt + Stage 2 context` |
| **Desktop Settings UI** | Engine Selector | `[P37] Groq Cloud selected`<br>`[P38] Local CPU selected` |
| | Live Diagnostics | `[P39] Test Mic (RMS VU meter response)`<br>`[P40] Test API Connection (ping round-trip, HTTP 200, 401, 403, timeout)` |
| | Floating Dock Badges | `[P41] 148px dock: 'Cloud Active' badge`<br>`[P42] 148px dock: 'Local CPU' badge`<br>`[P43] Language chip: 'HI-EN' / 'EN'` |

---

### 2.2 Boundary Value Analysis (BVA)

Critical numerical and structural boundaries tested:

| Metric / Boundary | Min / Below Valid | Nominal Value | Upper Boundary | Max / Above Valid | Test Target |
|-------------------|-------------------|---------------|----------------|-------------------|-------------|
| **Groq Cloud Latency** | 0.0 ms | ~280 ms | 349.9 ms | ≥ 350.0 ms (Fail) | Acceptance Criteria AC2.2 |
| **Local CPU Latency** | 0.0 ms | ~170 ms | 199.9 ms | ≥ 200.0 ms (Fail) | Acceptance Criteria AC2.2 |
| **Dialog Launch Latency** | 0.0 ms | ~18 ms | 49.9 ms | ≥ 50.0 ms (Fail) | Acceptance Criteria AC2.3 |
| **1-Click Word Removal** | 0.0 ms | ~0.6 ms | 49.9 ms | ≥ 50.0 ms (Fail) | Acceptance Criteria AC2.3 |
| **Accuracy Score** | < 0.0% (Clamped to 0.0%) | 0.0% – 100.0% | 100.0% (Clamped) | > 100.0% (Clamped to 100.0%) | `calibration_engine.py` |
| **Audio RMS Volume** | 0.0 (Silence) | 0.05 – 0.8 | 1.0 (Full scale) | > 1.0 (Normalized/prevent clipping) | `audio_engine.py`, `whisper_engine.py` |
| **Whisper Context Prompt** | 0 chars | 100 – 400 chars | 800 chars | > 800 chars (Safely truncated) | `voice_profile.py` |
| **Dock Idle Width** | 56 px (Legacy) | 148 px (Round 2) | 148 px | 188 px (Active Recording) | `ui/floating_widget.py` |

---

### 2.3 Pairwise Combinatorial Testing Matrix

We apply pairwise testing across major configuration parameters:
- **Engine**: `{Groq Cloud, Local CPU}`
- **Language Mode**: `{Hinglish, English}`
- **Speech Style**: `{Casual Chat, Developer Mode, Professional, Custom Persona}`
- **Dictionary Status**: `{Empty, Custom Word Present, Phonetic Replacement Present}`
- **Network State**: `{Online, Offline/Failover}`

Representative generated pairwise configurations:

| Case # | Engine | Language | Style | Dictionary | Network State | Expected Behavior |
|:------:|--------|----------|-------|------------|---------------|-------------------|
| **TC-PW1** | Groq Cloud | Hinglish | Casual Chat | Custom Word | Online | Romanized Hinglish, trailing punctuation stripped, custom word preserved, latency < 350ms |
| **TC-PW2** | Groq Cloud | Hinglish | Developer Mode | Phonetic Replacement | Online | Hinglish casing formatted (camelCase/snake_case), replacement applied with 100% fidelity |
| **TC-PW3** | Groq Cloud | English | Professional | Empty | Online | Well-punctuated English prose, no translation pass needed |
| **TC-PW4** | Groq Cloud | Hinglish | Custom Persona | Custom Word | Offline | Fails over to Local CPU, local fast Romanizer applies custom persona rules in < 200ms |
| **TC-PW5** | Local CPU | Hinglish | Casual Chat | Phonetic Replacement | Offline | Fast deterministic Devanagari Romanizer (<0.01ms), trailing punctuation removed, 0% GPU |
| **TC-PW6** | Local CPU | Hinglish | Developer Mode | Empty | Online | Local CPU transcribe + regex developer syntax transforms in < 200ms |
| **TC-PW7** | Local CPU | English | Casual Chat | Custom Word | Online | English casual lowercase, periods stripped, custom word retained |
| **TC-PW8** | Local CPU | Hinglish | Professional | Phonetic Replacement | Offline | Local fast Romanizer, capitalizes sentences, applies phonetic mapping |

---

### 2.4 Real-World Workloads & Benchmark Scenarios

The suite includes real-world end-to-end workload simulations:

1. **20-Case Natural Spoken Hinglish Benchmark (`benchmark_hinglish.py`)**:
   - 20 authoritative spoken Hindi/Hinglish sentences spanning:
     - Conversational daily speech ("Main thodi der mein call karta hoon")
     - Developer & DevOps workflows ("Staging server par deploy karke PR create kar raha hoon")
     - Team collaboration & office life ("Aaj ka meeting schedule kya hai?")
     - Professional & client communication ("Client ko presentation demo dikhana hai afternoon mein")
   - Verifies 5 mandatory assertions for each test case:
     a) Hindi input produces natural Romanized Hinglish in the Latin alphabet (no literal translation to English, no Devanagari characters).
     b) Technical English terms remain in clean English ("deploy", "server", "github", "commit", "PR", "database", "python").
     c) Saved personal dictionary words appear with 100% exact match fidelity.
     d) Casual Chat style strips trailing periods and commas while keeping Hinglish natural.
     e) End-to-end latency budget assertions (<350ms on Groq, <200ms on CPU).

2. **Complete Calibration-to-Dictation Lifecycle**:
   - Spoken audio -> Two-stage Romanization -> SequenceMatcher diff -> 1-click confirmation chip -> Voice profile registration -> Immediate biasing in subsequent live dictation.

3. **Live Desktop Diagnostics**:
   - Non-blocking audio RMS VU meter update loop.
   - Groq API connectivity probe measuring millisecond ping without freezing GUI event loop.

---

## 3. Test Suite Structure & Organization

```
whisper-flow/
├── TEST_INFRA.md                       # This document: Test infrastructure & methodology
├── benchmark_hinglish.py               # 20-case Hinglish benchmark script (<350ms Groq, <200ms CPU)
├── TEST_READY.md                       # Complete execution guide, test inventory, pass/fail status
└── tests/
    ├── __init__.py
    ├── test_hinglish_pipeline.py       # [R2-M1] Two-stage pipeline, acoustic capture, fast Romanizer, styles
    ├── test_two_stage_pipeline.py      # [R2-M1 Alias] Alias runner for two-stage pipeline tests
    ├── test_calibration_phonetic_memory.py # [R2-M2] 1-click chips, Heard->Target mapper, dual injection
    ├── test_phonetic_calibration.py    # [R2-M2 Alias] Alias runner for phonetic calibration tests
    ├── test_settings_ui_r2.py          # [R2-M3] Engine selector, live mic/API diagnostics, style cards, dock
    ├── test_desktop_lifecycle.py       # [Round 1] Win32 mutex, single-instance IPC, foreground activation
    ├── test_e2e_workflows.py           # [Round 1] End-to-end combination workflows
    ├── test_empirical_stress_m1.py     # [Round 1] Empirical stress tests and edge cases
    ├── test_final_acceptance_e2e.py    # [Round 1] AC1-AC7 acceptance criteria suite
    ├── test_m1_challenger2_stress.py   # [Round 1] UI presentation latency & capture safety
    ├── test_speech_calibration.py      # [Round 1] Diff computation, dataset validation, replacements
    ├── test_style_engine.py            # [Round 1] Casual, Developer, Persona style transforms
    ├── test_ui_responsiveness.py       # [Round 1] Sub-50ms dialog launch, 1-click removal latency
    └── test_whisper_engine.py          # [Round 1] CPU int8 model, Groq fallback, initial prompt
```

---

## 4. Test Verification Commands

### Full Regression & New Unit Tests
```powershell
.\.venv\Scripts\python.exe -m unittest discover -v tests
```

### 20-Case Automated Hinglish Benchmark
```powershell
.\.venv\Scripts\python.exe benchmark_hinglish.py
```
