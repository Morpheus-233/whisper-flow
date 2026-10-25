# WhisperFlow Engineering & Behavioral Guidelines

## 1. Secret Protection & Push Invariant
- NEVER write actual API keys, secrets, or tokens (`gsk_...`, `Bearer ...`) into source code, unit tests, analysis markdown documents, or agent handoffs.
- Always redact API keys in documentation using placeholder strings (e.g., `gsk_placeholder_redacted`).
- Ensure sensitive configuration files like `config.json` remain ignored by `.gitignore`.
- Before executing `git push`, verify that no staged or committed changes introduce secret strings.

## 2. Cloud Model Resilience & Fallbacks
- For third-party cloud LLM integrations (e.g., Groq API), never hardcode a single model identifier.
- Maintain an ordered list of candidate models (e.g., Qwen 27B, GPT-OSS 120B, LLaMA 70B) and dynamically fall back across candidates if a `404 Not Found` or deprecation error occurs.
- If all cloud models fail or network times out, ensure seamless fallback to deterministic local CPU processing without application crash.

## 3. Bilingual Hinglish & Smart Formatting Invariants
- **Romanization Over Translation**: Transcribe Hindi/Hinglish speech phonetically into the Latin alphabet. Never translate Hindi words into literal English.
- **Smart Retractions**: Spoken self-corrections ("no wait", "scratch that", "actually", "nahi wait") must discard the preceding aborted clause.
- **Structured Lists**: When speech enumerates items ("number one", "firstly", "three points"), format as clean multi-line Markdown lists.
