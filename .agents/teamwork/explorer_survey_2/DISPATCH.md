# Dispatch: Survey Explorer 2 (Speech & Style Engine Explorer)

**Role**: Speech & Style Engine Explorer
**Type**: teamwork_preview_explorer
**Working Directory**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_2
**Project Root**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
**Original Request**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md

## Objectives
1. Read ORIGINAL_REQUEST.md thoroughly.
2. Investigate all speech engine components, faster-whisper CPU int8 settings, Groq API fallback integration, vocabulary biasing (`initial_prompt`), and speech calibration mechanisms.
3. Investigate `data/calibration_sentences.json` (format, existing sentences vs requirement of 100 bilingual sentences: 50 English, 50 Hindi/Hinglish).
4. Investigate accuracy diff calculation, phonetic correction mapper, `voice_profile.py` / `voice_profile.json`, and dictionary replacement rules.
5. Investigate style transformations: Casual Chat (stripping trailing periods/commas/capitalization without GPU), Developer Mode (camelCase, snake_case, code syntax), and Custom Persona.
6. Detail gaps and concrete implementation requirements.
7. Write your complete findings to C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_2\handoff.md.
8. Send message to orchestrator upon completion.

## 2026-10-15T14:48:06Z
You are Survey Explorer 2 (Speech & Style Engine Explorer).
Your working directory is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_2
The project root is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
Read C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md and C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_2\DISPATCH.md before starting.
Perform a deep-dive investigation of speech engine components (faster-whisper CPU int8, Groq fallback, initial_prompt biasing), calibration sentences dataset (100 sentences: 50 English, 50 Hindi/Hinglish), phonetic correction mapper, voice_profile.py/json, and rule-based style transformations (Casual Chat, Developer Mode, Custom Persona).
Produce a comprehensive handoff report at C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_survey_2\handoff.md following the Handoff Protocol.
When finished, notify the orchestrator using send_message.
