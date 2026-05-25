@echo off
schtasks /create /tn "YukiBot_StartupRecovery" /tr "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%~dp0startup_recovery.ps1\"" /sc ONLOGON /ru "%USERNAME%" /delay 0000:30 /f
if %errorlevel% == 0 (
    echo OK: task registered.
) else (
    echo FAIL: run as administrator.
)
pause
