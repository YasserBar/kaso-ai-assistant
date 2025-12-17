@echo off
REM ================================================
REM Kaso AI Assistant - Full Project Setup
REM ================================================

echo.
echo ========================================
echo  Kaso AI Assistant - Full Setup
echo ========================================
echo.

REM Setup Backend
echo [Backend Setup]
echo ----------------------------------------
cd backend
call setup.bat
cd ..

echo.
echo [Frontend Setup]
echo ----------------------------------------
cd frontend
call setup.bat
cd ..

echo.
echo ========================================
echo  Full Setup Complete!
echo ========================================
echo.
echo To run the application:
echo.
echo   Terminal 1 (Backend):
echo     cd backend
echo     venv\Scripts\activate
echo     uvicorn app.main:app --reload
echo.
echo   Terminal 2 (Frontend):
echo     cd frontend
echo     npm run dev
echo.
echo Then open: http://localhost:3000
echo.
