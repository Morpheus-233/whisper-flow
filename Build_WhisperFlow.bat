@echo off
setlocal enabledelayedexpansion

:: Switch to script directory (handles spaces in paths)
cd /d "%~dp0"

set "PYTHON_EXE="
set "PYTHONW_EXE="

:: 1. Try Python Launcher (py -3)
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py -3"
    where pyw >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHONW_EXE=pyw -3"
    ) else (
        set "PYTHONW_EXE=py -3"
    )
    goto :PYTHON_FOUND
)

:: 2. Try standard python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    where pythonw >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHONW_EXE=pythonw"
    ) else (
        set "PYTHONW_EXE=python"
    )
    goto :PYTHON_FOUND
)

:PYTHON_MISSING
echo ======================================================================
echo Python 3.10 or newer was not detected on this system.
echo Whisper Flow requires Python 3.10+ to build its standalone package.
echo ======================================================================
echo.
set /p "CHOICE=Would you like to install Python 3.11 automatically via winget? (Y/N): "
if /i "%CHOICE%"=="Y" (
    echo.
    echo Attempting installation via Windows Package Manager (winget)...
    winget install Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
    if %errorlevel% equ 0 (
        echo.
        echo Python 3.11 installed successfully! Please restart this script.
        pause
        exit /b 0
    ) else (
        echo.
        echo Winget installation could not be completed.
    )
)

echo.
echo Opening python.org downloads page in your browser...
start https://www.python.org/downloads/
echo Please install Python 3.10 or newer (make sure to check "Add Python to PATH").
echo After installing, double-click Build_WhisperFlow.bat again.
echo.
pause
exit /b 1

:PYTHON_FOUND
:: Launch the build GUI using pythonw (no console window during build)
if not "%PYTHONW_EXE%"=="" (
    start "" %PYTHONW_EXE% build_gui.py
    if %errorlevel% equ 0 exit /b 0
)

:: Fallback if pythonw is unavailable: run in console mode
echo Starting Whisper Flow Builder in console mode...
%PYTHON_EXE% build_gui.py --cli
if %errorlevel% neq 0 (
    echo.
    echo Build failed. Check build_log.txt for details.
    pause
    exit /b 1
)
pause
exit /b 0
