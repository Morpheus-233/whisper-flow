# Dispatch: Worker M2 (Zero-GPU Speech Engine & Style Transforms)

**Role**: Zero-GPU Speech & Style Engine Worker
**Type**: teamwork_preview_worker
**Working Directory**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m2_1
**Project Root**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
**Original Request**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md
**Project Scope Document**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md

## Exclusive Write Ownership
You exclusively own:
- `whisper_engine.py`
- `config.py`
- `config.json`
- `text_cleaner.py`
- `style_engine.py`
You MUST NOT modify files outside your ownership scope.

## Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Objectives
1. Read ORIGINAL_REQUEST.md and PROJECT.md carefully.
2. Review Survey Explorer 1 and Explorer 2 handoffs:
   - `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_1\handoff.md`
   - `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_2\handoff.md`
3. Update `config.py` and `config.json`:
   - Set default `model_name` to multilingual `"base"` so bilingual Hindi/Hinglish speech decoding does not crash or fail.
4. Verify & Harden `whisper_engine.py`:
   - Ensure CPU int8 execution (`WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=6)`) consumes 0 MB GPU VRAM.
   - Ensure `initial_prompt` biasing is properly formatted and passed to `self.model.transcribe(..., initial_prompt=...)`.
   - Ensure Groq cloud fallback (`whisper-large-v3-turbo`) cleanly falls back to local CPU if the request fails or key is invalid.
5. Implement Rule-Based Transformations in `text_cleaner.py` / `style_engine.py`:
   - Casual Chat: Ensure `format_casual_chat` strips trailing formal periods/commas/capitalization without GPU.
   - Developer Mode: Implement instant rule-based conversion for spoken casing (`"camel case <words>"`, `"snake case <words>"`, `"kebab case <words>"`, `"pascal case <words>"`, `"constant case <words>"`) and spoken code syntax (`"dot env"` -> `.env`, `"arrow function"` -> `=>`, `"double equals"` -> `==`, `"open paren"` -> `(`, etc.).
   - Custom Persona: Implement rule-based persona transformations that format output according to user-defined tone without adding latency or requiring GPU LLMs.
6. Run unit tests and verification commands using `.\.venv\Scripts\python.exe`.
7. Write handoff report to `C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m2_1\handoff.md`.
8. Send completion message to orchestrator.


## 2026-10-15T14:59:46Z
You are Worker M2 (Zero-GPU Speech Engine & Style Transforms).
Your working directory is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m2_1
The project root is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
Read C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md, C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\orchestrator\PROJECT.md, and your dispatch at C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\worker_m2_1\DISPATCH.md before starting.
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
You exclusively own whisper_engine.py, config.py, config.json, text_cleaner.py, and style_engine.py.
Set multilingual "base" model default in config.py, verify 0 MB GPU VRAM in CPU int8, ensure initial_prompt biasing and Groq fallback failover, and implement instant rule-based transforms for Casual Chat, Developer Mode (camelCase/snake_case/syntax), and Custom Persona.
Run tests and write handoff.md in your working directory. Notify orchestrator via send_message when complete.
