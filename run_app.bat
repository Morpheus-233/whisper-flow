@echo off
title Whisper Flow Launcher
cd /d "%~dp0"
echo Starting Whisper Flow...
if exist ".venv\Scripts\python.exe" (
    call .venv\Scripts\python.exe app.py
) else (
    python app.py
)
if %errorlevel% neq 0 pause
