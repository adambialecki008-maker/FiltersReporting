@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

where pythonw.exe >nul 2>&1

if errorlevel 1 (
    echo ERROR: pythonw.exe not found in PATH.
    echo.
    echo Trying python.exe instead...
    echo.

    python "%~dp0opc_ua_server_simulator.py"

    exit /b %errorlevel%
)

start "" pythonw.exe "%~dp0opc_ua_server_simulator.py"

exit /b 0
