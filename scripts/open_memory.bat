@echo off
pushd "%~dp0.."
set "ROOT=%CD%"
popd
powershell -WindowStyle Hidden -Command "if (-not (netstat -ano | Select-String ':8765.*LISTENING')) { Start-Process -FilePath python -ArgumentList '%ROOT%\memory\admin\server.py' -WorkingDirectory '%ROOT%\memory\admin' -WindowStyle Hidden; Start-Sleep -Seconds 2 }; Start-Process 'http://127.0.0.1:8765/'"
