@echo off
setlocal
cd /d "%~dp0"
set "AGENT_MEMORY_ENABLED=true"
call 02_run_gaia_all.bat module04_memory
