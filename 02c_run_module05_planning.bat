@echo off
setlocal
cd /d "%~dp0"
set "AGENT_MEMORY_ENABLED=false"
set "AGENT_PLANNING_ENABLED=true"
call 02_run_gaia_all.bat module05_planning
