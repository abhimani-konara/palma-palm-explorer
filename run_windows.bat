@echo off
cd /d "%~dp0"
if not exist .venv python -m venv .venv
if not exist .venv\Scripts\python.exe goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
if not exist .env copy .env.example .env >nul
.venv\Scripts\python.exe app.py
pause
exit /b
:error
echo Setup failed. Install Python 3.11 or 3.12 with Add Python to PATH, then try again.
pause
