@echo off
REM ==============================================================================
REM ECES Egyptian Housing Pipeline & Dashboard - Windows One-Click Launcher
REM ==============================================================================

cd /d "%~dp0"

IF EXIST ".venv\Scripts\python.exe" (
    SET "PY_BIN=.venv\Scripts\python.exe"
) ELSE (
    SET "PY_BIN=python"
)

echo.
echo ==============================================================================
echo  Launching ECES Egyptian Housing Intelligence Dashboard
echo ==============================================================================
echo.

"%PY_BIN%" run.py %*

pause
