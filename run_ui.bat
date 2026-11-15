@echo off
title VICTOR // Personal AI Command Center
color 0B

echo =================================================================
echo             VICTOR PERSONAL AI COMMAND CENTER
echo         Futuristic JARVIS-Inspired Desktop Assistant
echo =================================================================
echo.
echo  [1] Launch Native Holographic Desktop UI (PySide6 / QML)
echo  [2] Launch Hands-Free Voice Console
echo  [3] Run Subsystem Diagnostics ^& Unit Tests
echo  [4] Re-calibrate / Train Custom 'Victor' Wake-Word Model
echo  [5] Launch Web Interface Fallback
echo.
echo =================================================================

set /p choice="Select an option (1-5) [Default 1]: "

if "%choice%"=="2" (
    echo Launching Voice Console...
    call "%~dp0.venv\Scripts\python.exe" "%~dp0run_victor.py" --voice
) else if "%choice%"=="3" (
    echo Running System Diagnostics...
    call "%~dp0.venv\Scripts\python.exe" "%~dp0run_victor.py" --test
) else if "%choice%"=="4" (
    echo Starting Custom Wake-Word Training...
    call "%~dp0.venv\Scripts\python.exe" "%~dp0run_victor.py" --train
) else if "%choice%"=="5" (
    echo Opening Web Interface...
    start "" "%~dp0src\ui\web\index.html"
) else (
    echo Launching Native Holographic Desktop Interface...
    call "%~dp0.venv\Scripts\python.exe" "%~dp0run_victor.py"
    if %errorlevel% neq 0 (
        echo.
        echo [!] Desktop UI exited with error code %errorlevel%.
        echo Falling back to opening Web Interface...
        start "" "%~dp0src\ui\web\index.html"
    )
)

echo.
pause
