@echo off
set "GPTSOVITS_DIR=F:\GPT-SoVITS-v2pro-20250604"
cd /d "%GPTSOVITS_DIR%"

echo [Yuki Voice API] Starting GPT-SoVITS API server on port 9880...
echo Model weights will be loaded on first synthesis call.
echo.

runtime\python.exe api_v2.py -a 127.0.0.1 -p 9880

pause
