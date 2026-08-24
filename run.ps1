# ==============================================================================
# ECES Egyptian Housing Pipeline & Dashboard - PowerShell Launcher
# ==============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PythonBin = if (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    "$ScriptDir\.venv\Scripts\python.exe"
} else {
    "python"
}

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host " 🚀 Launching ECES Egyptian Housing Intelligence Dashboard" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

& $PythonBin "$ScriptDir\run.py" $args
