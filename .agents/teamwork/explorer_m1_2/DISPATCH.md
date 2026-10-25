## 2026-10-22T10:09:32Z
[Message] timestamp=2026-10-22T10:09:32Z sender=b7127cef-b446-4dca-a8e7-b0da25424e7e priority=MESSAGE_PRIORITY_HIGH content=You are M1 Explorer 2 for Milestone M1 (Two-Stage Hinglish Pipeline).
Your working directory is: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\explorer_m1_2
Authoritative user request: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md (specifically see ## 2026-10-22T09:54:41Z).
Project architecture: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\PROJECT.md

Your task:
Investigate Stage 2 Fast Romanizer & Stylist in style_engine.py:
1. Design the Groq Cloud llama-3.3-70b-versatile prompt:
   - Must Romanize Hindi to Latin alphabet Hinglish (e.g. "Main kal code push kar dunga").
   - Strictly forbid English translation.
   - Preserve technical English words and code tokens ("deploy", "server", "github", "commit", "PR").
   - Enforce speech styles: Casual Chat (strip periods/commas), Developer Mode (camelCase, snake_case), Professional, Custom Persona.
2. Design the local offline CPU Romanizer fallback:
   - Fast rule-based Devanagari transliteration + common Hinglish lookup dictionary (sub-0.01ms).
   - Rule-based style transforms without GPU.
3. Define exact interface StyleEngine.format_two_stage(raw_text, style, voice_profile) and drop-in code recommendations.

Write analysis in analysis.md and a self-contained handoff.md. Notify when done via send_message.
