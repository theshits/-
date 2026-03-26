@echo off
chcp 65001 >nul 2>&1
title Air Pollution Simulation System - Stop Server

echo ========================================
echo   Air Pollution Simulation - Stop Server
echo ========================================
echo.

echo [1/4] Stopping uvicorn processes...
taskkill /f /im uvicorn.exe >nul 2>&1

echo [2/4] Stopping all Python processes using port 8080...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do (
    echo [Info] Found process PID %%a on port 8080
    taskkill /f /pid %%a >nul 2>&1
    if errorlevel 1 (
        echo [Warning] Could not terminate process %%a, trying force...
        taskkill /f /pid %%a /t >nul 2>&1
    )
)

timeout /t 1 /nobreak >nul

echo [3/4] Checking for remaining processes...
netstat -ano | findstr :8080 | findstr LISTENING >nul 2>&1
if errorlevel 1 (
    echo [Done] Port 8080 is free
) else (
    echo [Warning] Port 8080 is still in use
    echo [Info] Stopping all Python processes...
    taskkill /f /im python.exe >nul 2>&1
    taskkill /f /im pythonw.exe >nul 2>&1
    timeout /t 1 /nobreak >nul
)

echo [4/4] Final verification...
netstat -ano | findstr :8080 | findstr LISTENING >nul 2>&1
if errorlevel 1 (
    echo.
    echo ========================================
    echo   Server has been stopped successfully
    echo ========================================
) else (
    echo.
    echo [Error] Port 8080 is still in use
    echo [Info] Last attempt: Force stop by port...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080') do (
        taskkill /f /pid %%a /t >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
    
    netstat -ano | findstr :8080 | findstr LISTENING >nul 2>&1
    if errorlevel 1 (
        echo.
        echo ========================================
        echo   Server has been stopped successfully
        echo ========================================
    ) else (
        echo.
        echo [Error] Could not stop server automatically
        echo [Info] Please close the server window manually or restart computer
    )
)

echo.
pause
