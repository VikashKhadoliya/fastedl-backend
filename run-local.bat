@echo off
title FastEDL Local Launcher
echo ===================================================
echo Starting FastEDL Platform (Backend + Frontend)...
echo ===================================================

echo [1/2] Launching FastEDL Backend on port 8000...
start "FastEDL Backend (FastAPI :8000)" cmd /k ".\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo [2/2] Launching FastEDL Frontend on port 3000...
start "FastEDL Frontend (Next.js :3000)" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo FastEDL is up and running locally!
echo.
echo Public Website:     http://localhost:3000
echo Admin CMS Portal:   http://localhost:3000/admin/login
echo API Documentation:  http://localhost:8000/docs
echo.
echo Default Admin Credentials:
echo   Username: admin
echo   Password: FastEDL@Admin2026!
echo ===================================================
