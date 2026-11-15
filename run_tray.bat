@echo off
REM VICTOR Tray Mode - no window, just the notification-area icon.
REM Ctrl+Alt+V talk | Ctrl+Alt+T type | Ctrl+Alt+X stop
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo [!] Virtual environment not found at .venv
    echo     Create it first:  py -m venv .venv  ^&^&  .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "run_victor.py" --tray
exit /b 0
