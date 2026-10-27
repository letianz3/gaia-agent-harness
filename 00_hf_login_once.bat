@echo off
setlocal
cd /d "%~dp0"
set "HF_CLI=%~dp0.venv\Scripts\hf.exe"

if not exist "%HF_CLI%" (
  echo ERROR: Missing %HF_CLI%
  exit /b 1
)

echo Paste your fine-grained Hugging Face token at the secure prompt.
echo The token must read gaia-benchmark/GAIA and write zzzt19/gaia-baseline-agent.
"%HF_CLI%" auth login
