#!/bin/bash

echo "==================================="
echo "Face Recognition System - Dev Mode"
echo "==================================="
echo ""
echo "Starting Backend and Frontend..."
echo ""

# 백그라운드에서 백엔드 실행
cd backend
python server.py &
BACKEND_PID=$!
cd ..

# 백그라운드에서 프론트엔드 실행
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "==================================="
echo "Servers are running!"
echo "==================================="
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "==================================="
echo ""
echo "Press Ctrl+C to stop all servers..."

# Ctrl+C 시그널 처리
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'All servers stopped.'; exit" INT

# 프로세스가 종료될 때까지 대기
wait
