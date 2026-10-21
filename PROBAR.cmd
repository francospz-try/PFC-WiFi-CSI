@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto fin
".venv\Scripts\python.exe" verificar_web.py
:fin
pause
