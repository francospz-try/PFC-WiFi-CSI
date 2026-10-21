@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" iniciar.py
if errorlevel 1 pause
