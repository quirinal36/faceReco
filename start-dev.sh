#!/usr/bin/env bash

set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -z "${FACERECO_OPERATOR_TOKEN:-}" && -z "${FACERECO_OPERATOR_TOKEN_FILE:-}" ]]; then
    echo "Missing operator credential. Set FACERECO_OPERATOR_TOKEN or FACERECO_OPERATOR_TOKEN_FILE."
    echo "Generate a unique 32+ character secret; do not use .env.example placeholders."
    exit 1
fi

if [[ -z "${FACERECO_DEVICE_TOKEN:-}" && -z "${FACERECO_DEVICE_TOKEN_FILE:-}" ]]; then
    echo "Missing device credential. Set FACERECO_DEVICE_TOKEN or FACERECO_DEVICE_TOKEN_FILE."
    echo "The device credential must be 32+ characters and different from the operator credential."
    exit 1
fi

export FACERECO_BIND_HOST="${FACERECO_BIND_HOST:-127.0.0.1}"
export FACERECO_CORS_ORIGINS="${FACERECO_CORS_ORIGINS:-https://127.0.0.1:5173}"

if [[ "$FACERECO_BIND_HOST" == "0.0.0.0" || "$FACERECO_BIND_HOST" == "::" ]]; then
    echo "Wildcard listener addresses are forbidden. Use loopback or one explicit trusted LAN/VPN address."
    exit 1
fi

case "${FACERECO_ENV:-development}" in
    development)
        ;;
    prod|production)
        if [[ -n "${FACERECO_OPERATOR_TOKEN:-}" || -n "${FACERECO_DEVICE_TOKEN:-}" || -z "${FACERECO_OPERATOR_TOKEN_FILE:-}" || -z "${FACERECO_DEVICE_TOKEN_FILE:-}" ]]; then
            echo "Production requires FACERECO_OPERATOR_TOKEN_FILE and FACERECO_DEVICE_TOKEN_FILE; direct token values are development-only."
            exit 1
        fi
        if [[ "${FACERECO_ENCRYPTED_STORAGE_VERIFIED:-}" != "true" ]]; then
            echo "Production requires verified LUKS2/BitLocker storage and FACERECO_ENCRYPTED_STORAGE_VERIFIED=true."
            exit 1
        fi
        if [[ -z "${FACERECO_MODEL_ROOT:-}" ]]; then
            echo "Production requires FACERECO_MODEL_ROOT/models/buffalo_l/*.onnx (or the FACERECO_MODEL_NAME bundle); runtime downloads are forbidden."
            exit 1
        fi
        ;;
    *)
        echo "Unsupported FACERECO_ENV. Use development or production; unknown values fail closed."
        exit 1
        ;;
esac

echo "==================================="
echo "Face Recognition System - Dev Mode"
echo "==================================="
echo ""
echo "Starting Backend and Frontend..."
echo "Secrets are not displayed. FaceReco does not load .env.example."
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
echo "Backend:  http://${FACERECO_BIND_HOST}:8000"
echo "Frontend: https://127.0.0.1:5173"
echo "==================================="
echo ""
echo "Press Ctrl+C to stop all servers..."

# Ctrl+C 시그널 처리
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'All servers stopped.'; exit" INT

# 프로세스가 종료될 때까지 대기
wait
