@echo off
cd /d "%~dp0"

if "%1"=="stop" (
    echo Stopping Kneo Agent...
    taskkill /f /im python.exe >nul 2>&1
    echo Agent stopped.
    pause
    exit /b
)

echo Starting Kneo Agent...
call .venv\Scripts\activate.bat
python main.py
pause
