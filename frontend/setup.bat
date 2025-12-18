@echo off
REM ================================================
REM Kaso AI Assistant - Frontend Setup Script
REM ================================================

echo.
echo ========================================
echo  Kaso AI Assistant - Frontend Setup
echo ========================================
echo.

REM Check Node.js version
node --version 2>NUL
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org
    exit /b 1
)

REM Install dependencies
echo [1/3] Installing dependencies...
call npm install
echo       Dependencies installed.

REM Create .env.local if not exists
echo [2/3] Setting up environment...
if not exist ".env.local" (
    echo NEXT_PUBLIC_API_URL=/api > .env.local
    echo BACKEND_URL=http://backend:8000/api >> .env.local
    echo API_SECRET_KEY=change-me-in-production >> .env.local
    echo       Created .env.local file.
    echo.
    echo [IMPORTANT] Please edit .env.local:
    echo   - API_SECRET_KEY: Must match backend API_SECRET_KEY
    echo.
) else (
    echo       .env.local file already exists.
)

REM Build check
echo [3/3] Checking build...
call npm run lint
if errorlevel 1 (
    echo [WARNING] Lint errors found. Run 'npm run lint -- --fix' to fix.
)

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Make sure docker-compose is running: backend on http://localhost:8000
echo   2. Edit .env.local with your API key
echo   3. Run: npm run dev
echo   4. Open: http://localhost:3000
echo.
