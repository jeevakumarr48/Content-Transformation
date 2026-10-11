@echo off
setlocal enabledelayedexpansion
title TransformIQ Launcher
set "ROOT=%~dp0"

echo ============================================
echo   TRANSFORMIQ - starting local application
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python was not found on PATH.
  echo         Install Python 3.10+ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm was not found on PATH.
  echo         Install Node.js 18+ from https://nodejs.org
  pause
  exit /b 1
)

echo [1/4] Installing/checking backend dependencies...
pushd "%ROOT%backend"
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Backend dependencies could not be installed.
  popd
  pause
  exit /b 1
)
popd

echo [2/4] Checking frontend dependencies...
if not exist "%ROOT%frontend\node_modules" (
  echo       Installing frontend dependencies...
  pushd "%ROOT%frontend"
  call npm install
  popd
)

echo [3/4] Starting backend on http://localhost:8003 ...
start "TransformIQ Backend" /d "%ROOT%backend" cmd /k "python -m uvicorn main:app --host 127.0.0.1 --port 8003 --reload"

echo [4/4] Starting frontend on http://localhost:5174 ...
start "TransformIQ Frontend" /d "%ROOT%frontend" cmd /k "npm run dev -- --host 127.0.0.1"

echo.
echo Waiting for servers to come online...
timeout /t 7 /nobreak >nul
start "" "http://localhost:5174"

echo.
echo   Frontend : http://localhost:5174
echo   Backend  : http://localhost:8003
echo   API docs : http://localhost:8003/docs
echo.
echo Keep the two server windows open while using the app.
echo Run stop-transformiq.bat to shut everything down.
echo.
pause
