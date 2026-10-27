@echo off
setlocal
cd /d "%~dp0"
set "AGENT_MEMORY_ENABLED=false"
set "AGENT_PLANNING_ENABLED=true"
set "AGENT_RECOVERY_ENABLED=true"
set "AGENT_REPLANNING_ENABLED=true"
set "AGENT_PARALLEL_TOOLS_ENABLED=true"
set "AGENT_MAX_PARALLEL_TOOLS=3"
call 02_run_gaia_all.bat module07_parallel_tools
