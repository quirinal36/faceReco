@echo off
echo ===================================
echo Face Recognition System - Dev Mode
echo ===================================
echo.
echo Starting Backend and Frontend...
echo.

REM 백엔드와 프론트엔드를 새 터미널 창에서 실행
start "Backend Server" cmd /k "cd backend && call ..\venv\Scripts\activate.bat && python server.py"
start "Frontend Dev Server" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================
echo Servers are starting...
echo ===================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo ===================================
echo.
echo Press any key to stop all servers...
pause > nul

REM 서버 종료 (Python과 Node 프로세스)
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul

echo All servers stopped.
