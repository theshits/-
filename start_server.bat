@echo off
chcp 65001 >nul 2>&1
title Air Pollution Simulation System

echo ========================================
echo   Air Pollution Simulation - Start Server
echo ========================================
echo.

cd /d "%~dp0backend"

echo [1/4] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not detected, please install Python 3.10+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [2/4] Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [Info] Dependencies not installed, installing now...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [Error] Failed to install dependencies. Please run manually:
        echo        pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo [Done] Dependencies installed successfully
) else (
    echo [Done] Dependencies already installed
)

echo [3/4] Getting local IP address...
set LOCAL_IP=
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"Wireless LAN adapter Wi-Fi" /c:"Wireless LAN adapter WLAN"') do (
    for /f "tokens=2 delims=:" %%b in ('ipconfig ^| findstr /c:"IPv4 Address" /c:"IPv4" 2^>nul') do (
        for /f "tokens=1 delims= " %%c in ("%%b") do (
            set LOCAL_IP=%%c
            goto :got_ip
        )
    )
)

for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"Ethernet adapter"') do (
    for /f "tokens=2 delims=:" %%b in ('ipconfig ^| findstr /c:"IPv4 Address" /c:"IPv4" 2^>nul') do (
        for /f "tokens=1 delims= " %%c in ("%%b") do (
            set LOCAL_IP=%%c
            goto :got_ip
        )
    )
)

:got_ip
if "%LOCAL_IP%"=="" (
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address" /c:"IPv4" 2^>nul') do (
        for /f "tokens=1 delims= " %%b in ("%%a") do (
            set LOCAL_IP=%%b
            goto :ip_done
        )
    )
)

:ip_done
if "%LOCAL_IP%"=="" set LOCAL_IP=127.0.0.1

echo [Done] Local IP: %LOCAL_IP%

echo [4/4] Starting server...
echo.
echo ========================================
echo   Server started successfully!
echo.
echo   Local access:
echo     http://localhost:8080
echo.
echo   LAN access:
echo     http://%LOCAL_IP%:8080
echo.
echo   Press Ctrl+C to stop the server
echo ========================================
echo.

start "" "http://localhost:8080"

python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload

pause
