@echo off
cd /d "%~dp0"
echo Starting yukibot Memory Admin on http://127.0.0.1:8765 ...
python admin\server.py
pause
