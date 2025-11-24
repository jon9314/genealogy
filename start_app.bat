@echo off
echo Starting Genealogy App with OpenRouter LLM
echo ============================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop
echo.

REM Start backend
start "Backend" cmd /k "cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers started! Opening browser...
timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo Close this window or press Ctrl+C to stop monitoring
pause
