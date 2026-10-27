@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo ERROR: Missing %PYTHON%
  exit /b 1
)

echo [1/2] Ruff
"%PYTHON%" -m ruff check gaia_agent tests scripts app.py cli.py
if errorlevel 1 exit /b 1

echo [2/2] Pytest
"%PYTHON%" -m pytest -q
if errorlevel 1 exit /b 1

echo Local checks passed.
