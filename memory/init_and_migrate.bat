@echo off
cd /d "%~dp0"
echo [1/2] Initializing database...
python db.py
echo [2/2] Migrating existing JSON data...
python migrate.py
echo Done.
pause
