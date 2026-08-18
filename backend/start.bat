@echo off
setlocal
cd /d "%~dp0"

if not defined FACERECO_OPERATOR_TOKEN if not defined FACERECO_OPERATOR_TOKEN_FILE (
    echo Missing operator credential. Set FACERECO_OPERATOR_TOKEN or FACERECO_OPERATOR_TOKEN_FILE.
    exit /b 1
)
if not defined FACERECO_DEVICE_TOKEN if not defined FACERECO_DEVICE_TOKEN_FILE (
    echo Missing device credential. Set FACERECO_DEVICE_TOKEN or FACERECO_DEVICE_TOKEN_FILE.
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
REM Python 가상환경 활성화 및 서버 시작
call ..\venv\Scripts\activate.bat
python server.py
endlocal
