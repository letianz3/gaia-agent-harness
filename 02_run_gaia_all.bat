@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "RUN_LABEL=%~1"
if "%RUN_LABEL%"=="" set "RUN_LABEL=current"

if not exist "%PYTHON%" (
  echo ERROR: Missing %PYTHON%
  goto :failed
)

if "%OPENAI_API_KEY%"=="" for /f "usebackq delims=" %%K in (`powershell.exe -NoProfile -Command "[Environment]::GetEnvironmentVariable('OPENAI_API_KEY','User')"`) do set "OPENAI_API_KEY=%%K"
if "%OPENAI_API_KEY%"=="" (
  echo ERROR: OPENAI_API_KEY is unavailable. Run 00_save_openai_key_once.bat first.
  goto :failed
)

echo WARNING: This runs all 20 GAIA questions and consumes model API tokens.
"%PYTHON%" cli.py all
if errorlevel 1 goto :failed

"%PYTHON%" scripts\snapshot_run.py "%RUN_LABEL%"
if errorlevel 1 goto :failed

echo.
echo Completed. Results were saved under .runs and .runs\experiments.
pause
exit /b 0

:failed
echo.
echo Run failed. Review the error above.
pause
exit /b 1
