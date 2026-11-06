@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -X utf8 -B -m dashboard.server %*
if errorlevel 1 pause
