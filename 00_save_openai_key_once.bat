@echo off
setlocal
cd /d "%~dp0"

echo This stores OPENAI_API_KEY as a persistent Windows user environment variable.
echo The key is not written to this project or uploaded to Hugging Face.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$secure = Read-Host 'OpenAI API key' -AsSecureString; $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure); try { $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr); if ([string]::IsNullOrWhiteSpace($key)) { throw 'No key entered.' }; [Environment]::SetEnvironmentVariable('OPENAI_API_KEY', $key, 'User'); Write-Host 'OPENAI_API_KEY saved for this Windows user.' } finally { if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) } }"
if errorlevel 1 exit /b 1

echo Future runs of 02_run_gaia_all.bat will load it automatically.
