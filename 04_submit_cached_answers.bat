@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo ERROR: Missing %PYTHON%
  exit /b 1
)

if not exist ".runs\answers.json" (
  echo ERROR: .runs\answers.json does not exist. Run 02_run_gaia_all.bat first.
  exit /b 1
)

set "RESULT_FILE=.runs\last_submission.txt"
"%PYTHON%" -c "import json; from gaia_agent.config import Settings; from gaia_agent.evaluator import EvaluationRunner, ScoringClient; s=Settings.from_env(); results=json.loads((s.runs_dir/'answers.json').read_text(encoding='utf-8')); answers=EvaluationRunner.submission_answers(results); print(ScoringClient(s).submit('zzzt19','https://huggingface.co/spaces/zzzt19/gaia-baseline-agent/tree/main',answers))" > "%RESULT_FILE%" 2>&1
set "RESULT_CODE=%ERRORLEVEL%"

type "%RESULT_FILE%"
echo.
echo Result saved to %RESULT_FILE%
pause
exit /b %RESULT_CODE%
