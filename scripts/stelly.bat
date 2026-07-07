@echo off
REM Starts Stelly on Windows. Used by the startup shortcut that
REM install_startup_windows.ps1 creates, also fine to double click.
cd /d "%~dp0.."
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python main.py
pause
