@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo ERROR: Missing %PYTHON%
  exit /b 1
)

"%PYTHON%" -c "from huggingface_hub import HfApi, get_token; assert get_token(), 'Run 00_hf_login_once.bat first'; HfApi().upload_folder(folder_path='.', repo_id='zzzt19/gaia-baseline-agent', repo_type='space', allow_patterns=['README.md','index.html','app.py','cli.py','requirements.txt','.env.example','*.bat','gaia_agent/*.py','tests/*.py','scripts/*.py'], commit_message='Update GAIA baseline agent')"
if errorlevel 1 exit /b 1

echo Published: https://huggingface.co/spaces/zzzt19/gaia-baseline-agent/tree/main
