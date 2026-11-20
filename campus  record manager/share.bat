@echo off
title Campus Record Manager - Public Sharing Link
color 0b
echo ========================================================
echo   CAMPUS RECORD MANAGER - 24/7 SHAREABLE LINK
echo ========================================================
echo.
echo Checking backend server on localhost:5000...
netstat -ano | findstr :5000 >nul
if %errorlevel% neq 0 (
    echo Starting backend server in background...
    start /b python app.py
    timeout /t 3 /nobreak >nul
) else (
    echo Backend server is already running!
)

echo Starting Cloudflare Tunnel Daemon...
python tunnel_daemon.py
pause
