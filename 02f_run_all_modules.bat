@echo off
setlocal
cd /d "%~dp0"
set "AGENT_MEMORY_ENABLED=true"
set "AGENT_PLANNING_ENABLED=true"
set "AGENT_RECOVERY_ENABLED=true"
set "AGENT_REPLANNING_ENABLED=true"
set "AGENT_PARALLEL_TOOLS_ENABLED=true"
set "AGENT_MULTI_AGENT_ENABLED=true"
set "AGENT_LLM_CACHE_ENABLED=true"
set "AGENT_MAX_LLM_CALLS=100"
call 02_run_gaia_all.bat all_modules
