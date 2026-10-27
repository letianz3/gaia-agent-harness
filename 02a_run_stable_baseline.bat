@echo off
setlocal
cd /d "%~dp0"
set "AGENT_MEMORY_ENABLED=false"
call 02_run_gaia_all.bat stable_baseline
