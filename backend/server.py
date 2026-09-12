"""
FastAPI 서버 애플리케이션

얼굴 인식 시스템 웹 API 서버
"""

import ipaddress
import os
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

# API 라우트 import
from api.routes import (
    router,
    cleanup_resources,
    get_face_database,
)
from models.face_recognition import validate_model_artifacts
from security import (
    ApiSecurityMiddleware,
    get_cors_origins,
    get_environment,
    validate_security_configuration,
)
from utils.upload_limits import (
    UploadBodyLimitMiddleware,
    configure_multipart_memory_limit,
)


def _environment() -> str:
    return get_environment()


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def get_bind_host() -> str:
    """Return a fail-safe listener address for the local management API."""
    host = os.getenv("FACERECO_BIND_HOST", "127.0.0.1").strip()
    if not host:
        raise RuntimeError("FACERECO_BIND_HOST cannot be empty")

    is_loopback = host.lower() == "localhost"
    try:
        address = ipaddress.ip_address(host)
        if address.is_unspecified or address.is_multicast or address.is_global:
            raise RuntimeError(
                "FACERECO_BIND_HOST must name one explicit local or private interface address"
            )
        is_loopback = is_loopback or address.is_loopback
    except ValueError:
        if not is_loopback:
            raise RuntimeError("FACERECO_BIND_HOST must be an explicit IP address")

    if _environment() == "production" and not is_loopback:
        raise RuntimeError("Production edge API must bind to a loopback address")

    if not is_loopback and not _is_true(os.getenv("FACERECO_ALLOW_NON_LOOPBACK")):
        raise RuntimeError(
            "Non-loopback binding requires FACERECO_ALLOW_NON_LOOPBACK=true and a trusted LAN/VPN boundary"
        )

    return host


def _request_arrived_on_configured_listener(scope) -> bool:
    """Verify the accepted socket matches the configured local interface.

    This is a defense-in-depth check for alternate ASGI launch commands. It
    does not replace binding/firewall policy, but prevents a wildcard Uvicorn
    CLI argument from silently widening the application's data boundary.
    """
    server_address = scope.get("server")
    if server_address is None:
        # A Unix-domain socket has no TCP listener address and is local-only.
        return True
    if not server_address or not server_address[0]:
        return False

    actual_host = str(server_address[0]).strip()
    expected_host = get_bind_host()
    try:
        actual_address = ipaddress.ip_address(actual_host)
    except ValueError:
        return False

    if expected_host.lower() == "localhost":
        return actual_address.is_loopback
    try:
        return actual_address == ipaddress.ip_address(expected_host)
    except ValueError:
        return False


class ListenerBoundaryMiddleware:
    """Reject HTTP traffic accepted on an unintended network interface."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not _request_arrived_on_configured_listener(scope):
            response = JSONResponse(
                {"detail": "Not found"},
                status_code=404,
                headers={
                    "Cache-Control": "private, no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


# ==================== 애플리케이션 라이프사이클 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management

    Startup: Initialize resources
    Shutdown: Cleanup resources
    """
    # Fail before initializing storage, models, or cameras if auth is unsafe.
    validate_security_configuration()
    get_bind_host()
    validate_model_artifacts()

    # Startup
    print("=" * 60)
    print("Starting Face Recognition API Server...")
    print("=" * 60)

    # Initial load (dependencies will be initialized automatically)
    print("API routes loaded successfully")

    # Audit/repair the full private data tree before accepting any request.
    face_database = get_face_database()
    if not face_database.is_available:
        raise RuntimeError("Face store could not be loaded safely")
    print("Face database initialized")

    yield

    # Shutdown
    print("\n" + "=" * 60)
    print("Shutting down server...")
    cleanup_resources()
    print("Resources cleaned up successfully")
    print("=" * 60)


# ==================== FastAPI 애플리케이션 생성 ====================

production = _environment() == "production"
configure_multipart_memory_limit()

app = FastAPI(
    title="얼굴 인식 API",
    description="실시간 얼굴 감지 및 인식 시스템 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if production else "/docs",
    redoc_url=None if production else "/redoc",
    openapi_url=None if production else "/openapi.json",
)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(_request, _error):
    """Do not reflect request values (names, IDs, or form metadata) in errors."""
    return JSONResponse(status_code=422, content={"detail": "Invalid request"})


# ==================== CORS 설정 ====================

# This is added first so it is inside authentication in the final ASGI stack.
# It never receives an unauthorized upload body.
app.add_middleware(UploadBodyLimitMiddleware)

# Authenticate first in the inner application; CORS wraps it only to service
# explicitly allowed browser origins and credential-free preflight requests.
app.add_middleware(ApiSecurityMiddleware)

# CORS is a browser policy, not an authentication or network boundary.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_cors_origins()),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

# Last-added middleware is outermost in Starlette, so the listener boundary
# runs before CORS, authentication, multipart parsing, or route dependencies.
app.add_middleware(ListenerBoundaryMiddleware)


# ==================== 라우터 등록 ====================

app.include_router(router)


# ==================== 루트 엔드포인트 ====================

@app.get("/")
async def root():
    """
    루트 엔드포인트

    API 정보 및 사용 가능한 엔드포인트 안내
    """
    return {
        "message": "얼굴 인식 API 서버",
        "version": "1.0.0",
        "status": "/api/health",
    }


# ==================== 메인 함수 ====================

def main():
    """
    서버 실행 함수

    개발 모드로 Uvicorn 서버 시작
    """
    print("\n" + "=" * 60)
    print("Starting FastAPI server...")
    print("=" * 60)
    host = get_bind_host()
    print(f"Server URL: http://{host}:8000")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server.\n")

    uvicorn.run(
        "server:app",
        host=host,
        port=8000,
        reload=not production and _is_true(os.getenv("FACERECO_RELOAD")),
        log_level="info",
        access_log=False,
        proxy_headers=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
