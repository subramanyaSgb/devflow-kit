@echo off
REM Locate a Python 3 and run the guard; fail open if none is found.
py -3 "%~dp0devlog_guard.py" 2>nul && exit /b 0
python "%~dp0devlog_guard.py" 2>nul && exit /b 0
python3 "%~dp0devlog_guard.py" 2>nul && exit /b 0
exit /b 0
