@echo off
setlocal EnableExtensions
title File Archive System - Web

set "SCRIPT_DIR=%~dp0"
set "WEB_DIR=%SCRIPT_DIR%web_system"
set "ADMIN_TOKEN=admin-default-token"

if not exist "%WEB_DIR%\app.py" (
    echo [ERROR] Cannot find "%WEB_DIR%\app.py"
    echo Please make sure this script is inside project root.
    pause
    exit /b 1
)

if exist "%SCRIPT_DIR%config.env" (
    for /f "tokens=1,* delims==" %%A in (%SCRIPT_DIR%config.env) do (
        if /i "%%A"=="ADMIN_TOKEN" set "ADMIN_TOKEN=%%B"
    )
)

if not exist "%WEB_DIR%\data" mkdir "%WEB_DIR%\data"

echo ========================================
echo File Archive System - Web Service
echo ========================================
echo URL:  http://127.0.0.1:5000
echo Admin URL: http://127.0.0.1:5000/?token=%ADMIN_TOKEN%
echo Press Ctrl+C to stop.
echo.

pushd "%WEB_DIR%"
python app.py
set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Web service exited with code %EXIT_CODE%.
)
pause
exit /b %EXIT_CODE%
