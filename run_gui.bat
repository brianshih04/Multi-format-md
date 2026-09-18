@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Runtime not installed. Run setup_windows.ps1 first.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "doc_to_md_gui.py"
