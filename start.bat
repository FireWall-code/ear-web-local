@echo off
SETLOCAL EnableDelayedExpansion
title Ear Web Bridge - Launcher

:: Color definition (Light Red on Black)
color 0C

:HEADER
echo.
echo  ==========================================================
echo  =                                                        =
echo  =                 EAR WEB BRIDGE FIX                     =
echo  =              Advanced Bluetooth Bridge                 =
echo  =                                                        =
echo  ==========================================================
echo.

:CHECK_PYTHON
echo  [*] Checking environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [!] ERROR: Python is not installed or not in PATH.
    echo      Please install Python 3.10+ and check "Add to PATH".
    echo.
    echo      Download: https://www.python.org/
    echo.
    pause
    exit /b
)
echo  [+] Python found!
echo.

:START_BRIDGE
echo  [*] Starting Bridge...
echo.
:: Run directly in the same window
python bridge.py

:: If bridge.py exits, the script continues here
echo.
echo  [-] Bridge closed.
timeout /t 2 >nul
exit
