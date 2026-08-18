@echo off
setlocal
cd /d "%~dp0"

if not defined FACERECO_OPERATOR_TOKEN if not defined FACERECO_OPERATOR_TOKEN_FILE (
    echo Missing operator credential. Set FACERECO_OPERATOR_TOKEN or FACERECO_OPERATOR_TOKEN_FILE.
    echo Generate a unique 32+ character secret; do not use .env.example placeholders.
    exit /b 1
)

if not defined FACERECO_DEVICE_TOKEN if not defined FACERECO_DEVICE_TOKEN_FILE (
    echo Missing device credential. Set FACERECO_DEVICE_TOKEN or FACERECO_DEVICE_TOKEN_FILE.
    echo The device credential must be 32+ characters and different from the operator credential.
    exit /b 1
)

if not defined FACERECO_BIND_HOST set "FACERECO_BIND_HOST=127.0.0.1"
if not defined FACERECO_CORS_ORIGINS set "FACERECO_CORS_ORIGINS=https://127.0.0.1:5173"
if "%FACERECO_BIND_HOST%"=="0.0.0.0" (
    echo Wildcard listener addresses are forbidden. Use loopback or one explicit trusted LAN/VPN address.
    exit /b 1
)
if "%FACERECO_BIND_HOST%"=="::" (
    echo Wildcard listener addresses are forbidden. Use loopback or one explicit trusted LAN/VPN address.
    exit /b 1
)

if not defined FACERECO_ENV set "FACERECO_ENV=development"
if /I "%FACERECO_ENV%"=="development" goto configuration_ready
if /I "%FACERECO_ENV%"=="prod" goto check_production
if /I "%FACERECO_ENV%"=="production" goto check_production
echo Unsupported FACERECO_ENV. Use development or production; unknown values fail closed.
exit /b 1

:check_production
if defined FACERECO_OPERATOR_TOKEN (
    echo Production requires file-backed credentials; FACERECO_OPERATOR_TOKEN is development-only.
    exit /b 1
)
if defined FACERECO_DEVICE_TOKEN (
    echo Production requires file-backed credentials; FACERECO_DEVICE_TOKEN is development-only.
    exit /b 1
)
if not defined FACERECO_OPERATOR_TOKEN_FILE (
    echo Production requires FACERECO_OPERATOR_TOKEN_FILE.
    exit /b 1
)
if not defined FACERECO_DEVICE_TOKEN_FILE (
    echo Production requires FACERECO_DEVICE_TOKEN_FILE.
    exit /b 1
)
if /I not "%FACERECO_ENCRYPTED_STORAGE_VERIFIED%"=="true" (
    echo Production requires verified BitLocker storage and FACERECO_ENCRYPTED_STORAGE_VERIFIED=true.
    exit /b 1
)
if not defined FACERECO_MODEL_ROOT (
    echo Production requires FACERECO_MODEL_ROOT\models\buffalo_l\*.onnx or the FACERECO_MODEL_NAME bundle; runtime downloads are forbidden.
    exit /b 1
)

:configuration_ready
echo ===================================
echo Face Recognition System - Dev Mode
echo ===================================
echo.
echo Starting Backend and Frontend...
echo Secrets are not displayed. FaceReco does not load .env.example.
echo.

REM 백엔드와 프론트엔드를 새 터미널 창에서 실행
start "Backend Server" cmd /k "cd backend && call ..\venv\Scripts\activate.bat && python server.py"
start "Frontend Dev Server" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================
echo Servers are starting...
echo ===================================
echo Backend:  http://%FACERECO_BIND_HOST%:8000
echo Frontend: https://127.0.0.1:5173
echo ===================================
echo.
echo Press any key to stop all servers...
pause > nul

REM 서버 종료 (Python과 Node 프로세스)
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul

echo All servers stopped.
endlocal
