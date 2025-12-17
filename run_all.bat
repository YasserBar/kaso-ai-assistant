@echo off
setlocal enableextensions

REM Kaso AI Assistant - One-click runner (Backend + Frontend)
REM This script starts the FastAPI backend and Next.js frontend in separate windows.

TITLE Kaso AI Assistant Runner

REM Check environment files
if not exist backend\.env (
  echo [Warning] backend\.env not found. Please create it based on backend\.env.example.
) else (
  echo [OK] backend\.env found.
)
if not exist frontend\.env.local (
  echo [Warning] frontend\.env.local not found. Please create it based on frontend\env.example.txt.
) else (
  echo [OK] frontend\.env.local found.
)

REM Optionally ensure Docker services (e.g., database) are running
REM Uncomment the following lines if you want to auto-start docker-compose
REM if exist docker-compose.yml (
REM   echo [Info] Starting docker-compose services in the background...
REM   docker-compose up -d
REM )

REM Start Backend server (FastAPI) in a new window
start "Kaso Backend" cmd /k "cd /d backend && venv\Scripts\activate && uvicorn app.main:app --reload"

REM Start Frontend server (Next.js) in a new window
start "Kaso Frontend" cmd /k "cd /d frontend && npm run dev"

REM Open browser to frontend
start "Browser" http://localhost:3000/

echo.
echo ========================================
echo Started Kaso Backend and Frontend.
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:3000
echo ========================================
echo.

echo If a port is busy, Next.js may use another port automatically.
echo Check the opened windows for logs.

endlocal