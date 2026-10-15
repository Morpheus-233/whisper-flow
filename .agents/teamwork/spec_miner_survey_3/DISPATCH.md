# Dispatch: Survey Spec Miner 3 (Desktop Lifecycle & Testing Spec Miner)

**Role**: Desktop Lifecycle & Testing Spec Miner
**Type**: teamwork_preview_spec_miner
**Working Directory**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\spec_miner_survey_3
**Project Root**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
**Original Request**: C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md

## Objectives
1. Read ORIGINAL_REQUEST.md thoroughly.
2. Probe specifications, requirements, and existing implementation of Desktop Lifecycle, Single-Instance Management, Windows named mutex, IPC server/client, and AllowSetForegroundWindow foreground activation.
3. Investigate UI responsiveness requirements: opening dialogs (Preferences, Voice Calibration Wizard) in <50ms with dark title bars (DWMWA_USE_IMMERSIVE_DARK_MODE) and zero Win32 mouse capture deadlock.
4. Probe 1-click instant word and replacement rule removal with real-time search filtering.
5. Probe testing suite setup: `python -m unittest discover tests`, test structure, existing test cases, and test harness requirements for all acceptance criteria.
6. Write your complete findings to C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\spec_miner_survey_3\handoff.md.
7. Send message to orchestrator upon completion.

## 2026-10-15T14:48:06Z
You are Survey Spec Miner 3 (Desktop Lifecycle & Testing Spec Miner).
Your working directory is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\spec_miner_survey_3
The project root is C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow
Read C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\ORIGINAL_REQUEST.md and C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\spec_miner_survey_3\DISPATCH.md before starting.
Investigate desktop lifecycle specifications, single-instance Windows named mutex, IPC server/client, AllowSetForegroundWindow foreground activation, UI responsiveness (<50ms dialog opening, DWM dark mode, Win32 mouse capture deadlock avoidance), 1-click word removal with search filtering, and unit/E2E test suite setup.
Produce a comprehensive handoff report at C:\Users\Admin\.gemini\antigravity\scratch\whisper-flow\.agents\teamwork\spec_miner_survey_3\handoff.md following the Handoff Protocol.
When finished, notify the orchestrator using send_message.
