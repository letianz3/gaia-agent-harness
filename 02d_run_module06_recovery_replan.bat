@echo off
setlocal
cd /d "%~dp0"
set "AGENT_MEMORY_ENABLED=false"
set "AGENT_PLANNING_ENABLED=true"
set "AGENT_RECOVERY_ENABLED=true"
set "AGENT_REPLANNING_ENABLED=true"
call 02_run_gaia_all.bat module06_conservative_replan
