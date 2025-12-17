@echo off
REM ================================================
REM Kaso AI Assistant - Backend Setup Script
REM ================================================

echo.
echo ========================================
echo  Kaso AI Assistant - Backend Setup
echo ========================================
echo.

REM Check Python version
python --version 2>NUL
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    exit /b 1
)

REM Create virtual environment
echo [1/5] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo       Virtual environment created.
) else (
    echo       Virtual environment already exists.
)

REM Activate virtual environment
echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [3/5] Upgrading pip...
python -m pip install --upgrade pip -q

REM Install dependencies
echo [4/5] Installing dependencies...
pip install -r requirements.txt -q
pip install -r requirements-test.txt -q
echo       Dependencies installed.

REM Create .env if not exists
echo [5/5] Setting up environment...
if not exist ".env" (
    copy .env.example .env
    echo       Created .env file from template.
    echo.
    echo [IMPORTANT] Please edit .env and add your API keys:
    echo   - GROQ_API_KEY: Get from https://console.groq.com/
    echo   - API_SECRET_KEY: Generate a random key
    echo.
) else (
    echo       .env file already exists.
)

REM Create data directories
if not exist "data\raw" mkdir data\raw
if not exist "data\processed" mkdir data\processed
if not exist "data\chunks" mkdir data\chunks

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Edit .env with your API keys
echo   2. Run: python -m data_pipeline.run_pipeline --markdown "../kaso_research_report.md"
echo   3. Start server: uvicorn app.main:app --reload
echo.
