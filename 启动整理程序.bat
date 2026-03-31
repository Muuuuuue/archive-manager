@echo off
setlocal EnableExtensions
title File Archive System - Organizer

set "SCRIPT_DIR=%~dp0"
set "ORG_DIR=%SCRIPT_DIR%file_organizer"

if not exist "%ORG_DIR%\main.py" (
    echo [ERROR] Cannot find "%ORG_DIR%\main.py"
    echo Please make sure this script is inside project root.
    pause
    exit /b 1
)

echo ========================================
echo File Archive System - Organizer
echo ========================================
echo [1] Run once (manual)
echo [2] Run scheduler (hourly)
echo [3] Run weekly report
echo.
set /p choice=Choose (1/2/3): 

pushd "%ORG_DIR%"
if "%choice%"=="1" (
    echo.
    echo Running once...
    python main.py once
) else if "%choice%"=="2" (
    echo.
    echo Running scheduler... Press Ctrl+C to stop.
    python main.py scheduler
) else if "%choice%"=="3" (
    echo.
    echo Running weekly report...
    python main.py report
) else (
    echo Invalid option: %choice%
)
set "EXIT_CODE=%ERRORLEVEL%"
popd

echo.
if not "%EXIT_CODE%"=="0" echo [WARN] Exit code: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
