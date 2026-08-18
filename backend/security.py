"""Authentication and deployment-boundary configuration for the edge API."""

from __future__ import annotations

import os
import re
import secrets
import stat
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import FrozenSet, Optional, Pattern, Sequence, Tuple
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.responses import JSONResponse


MIN_TOKEN_LENGTH = 32
DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost:5173",
    "https://127.0.0.1:5173",
)
ENVIRONMENT_ALIASES = {
    "development": "development",
    "prod": "production",
    "production": "production",
}


class Role(str, Enum):
    """Roles recognized by the local edge API."""

    OPERATOR = "operator"
    DEVICE = "device"


@dataclass(frozen=True)
class Principal:
    """Authenticated caller."""

    role: Role
    subject: str


class AccessPolicy(str, Enum):
    """Authorization policy applied before FastAPI reads a request body."""

    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    OPERATOR = "operator"
    DEVICE = "device"


@dataclass(frozen=True)
class SecurityConfig:
    """Validated security settings loaded from environment or secret files."""

    operator_token: str
    device_token: str
    environment: str
    cors_origins: Tuple[str, ...]
    encrypted_storage_verified: bool


bearer_scheme = HTTPBearer(auto_error=False)


_POLICY_RULES: Sequence[Tuple[FrozenSet[str], Pattern[str], AccessPolicy]] = (
    (frozenset({"GET"}), re.compile(r"^/api/health$"), AccessPolicy.PUBLIC),
    (
        frozenset({"GET"}),
        re.compile(r"^/api/auth/whoami$"),
        AccessPolicy.AUTHENTICATED,
    ),
    (
        frozenset({"POST"}),
        re.compile(r"^/api/face/register$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"POST"}),
        re.compile(r"^/api/face/[^/]+/add-sample$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"GET"}),
        re.compile(r"^/api/faces/list$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"GET"}),
        re.compile(r"^/api/faces/[^/]+/thumbnail$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"DELETE"}),
        re.compile(r"^/api/face/[^/]+$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"POST"}),
        re.compile(r"^/api/faces/merge$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"GET"}),
        re.compile(r"^/api/camera/(stream|stats)$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"POST"}),
        re.compile(r"^/api/camera/(release|reopen)$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"GET"}),
        re.compile(r"^/api/attendance/(today|range|stats)$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"GET"}),
        re.compile(r"^/api/attendance/date/[^/]+$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"POST"}),
        re.compile(r"^/api/attendance/person/search$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"DELETE"}),
        re.compile(r"^/api/attendance/[^/]+$"),
        AccessPolicy.OPERATOR,
    ),
    (
        frozenset({"POST"}),
        re.compile(r"^/api/liveness/(start|check|status)$"),
        AccessPolicy.DEVICE,
    ),
)


def _read_secret(name: str) -> str:
    """Read a secret from ``NAME`` or ``NAME_FILE`` without logging it."""
    value = os.getenv(name)
    file_value = os.getenv(f"{name}_FILE")

    if value and file_value:
        raise RuntimeError(f"Configure only one of {name} and {name}_FILE")

    if file_value:
        secret_path = Path(file_value).expanduser()
        if secret_path.is_symlink() or not secret_path.is_file():
            raise RuntimeError(f"{name}_FILE must reference a regular file")

        if os.name == "posix":
            mode = stat.S_IMODE(secret_path.stat().st_mode)
            if mode & 0o077:
                raise RuntimeError(f"{name}_FILE must not be accessible by group or others")

        return secret_path.read_text(encoding="utf-8").strip()

    return (value or "").strip()


def _parse_bool(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def get_environment() -> str:
    """Return a validated, canonical deployment environment.

    Unknown values must fail closed: a typo in ``production`` must never disable
    the production listener, model-provisioning, or encrypted-storage gates.
    """
    raw_environment = os.getenv("FACERECO_ENV", "development").strip().lower()
    environment = ENVIRONMENT_ALIASES.get(raw_environment)
    if environment is None:
        raise RuntimeError(
            "FACERECO_ENV must be one of: development, prod, production"
        )
    return environment


def _parse_cors_origins(raw_origins: Optional[str]) -> Tuple[str, ...]:
    origins = (
        tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
        if raw_origins is not None
        else DEFAULT_CORS_ORIGINS
    )

    for origin in origins:
        if origin == "*":
            raise RuntimeError("Wildcard CORS origins are forbidden")

        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError("CORS origins must be explicit HTTP(S) origins")

    return origins


def get_cors_origins() -> Tuple[str, ...]:
    """Return the explicit browser-origin allowlist without loading credentials."""
    return _parse_cors_origins(os.getenv("FACERECO_CORS_ORIGINS"))


@lru_cache(maxsize=1)
def get_security_config() -> SecurityConfig:
    """Load and validate fail-closed API security configuration."""
    operator_token = _read_secret("FACERECO_OPERATOR_TOKEN")
    device_token = _read_secret("FACERECO_DEVICE_TOKEN")
    environment = get_environment()

    if len(operator_token) < MIN_TOKEN_LENGTH or len(device_token) < MIN_TOKEN_LENGTH:
        raise RuntimeError(
            f"Operator and device tokens must each contain at least {MIN_TOKEN_LENGTH} characters"
        )

    if secrets.compare_digest(operator_token, device_token):
        raise RuntimeError("Operator and device tokens must be different")

    encrypted_storage_verified = _parse_bool(
        os.getenv("FACERECO_ENCRYPTED_STORAGE_VERIFIED")
    )
    if environment == "production" and not encrypted_storage_verified:
        raise RuntimeError(
            "Production requires verified encrypted storage "
            "(set FACERECO_ENCRYPTED_STORAGE_VERIFIED=true)"
        )
    if environment == "production" and (
        not os.getenv("FACERECO_OPERATOR_TOKEN_FILE")
        or not os.getenv("FACERECO_DEVICE_TOKEN_FILE")
    ):
        raise RuntimeError(
            "Production requires file-backed operator and device credentials"
        )

    return SecurityConfig(
        operator_token=operator_token,
        device_token=device_token,
        environment=environment,
        cors_origins=get_cors_origins(),
        encrypted_storage_verified=encrypted_storage_verified,
    )


def validate_security_configuration() -> SecurityConfig:
    """Validate configuration at startup so the server cannot run open by mistake."""
    return get_security_config()


def get_api_policy(method: str, path: str) -> Optional[AccessPolicy]:
    """Resolve the explicit policy for an API method/path pair."""
    normalized_method = method.upper()
    for methods, pattern, policy in _POLICY_RULES:
        if normalized_method in methods and pattern.fullmatch(path):
            return policy
    return None


def _principal_from_token(token: str) -> Optional[Principal]:
    config = get_security_config()
    if secrets.compare_digest(token, config.operator_token):
        return Principal(role=Role.OPERATOR, subject="local-operator")
    if secrets.compare_digest(token, config.device_token):
        # The P0 edge profile intentionally supports one local kiosk principal.
        return Principal(role=Role.DEVICE, subject="local-device")
    return None


def principal_from_authorization_header(value: Optional[str]) -> Optional[Principal]:
    """Parse and authenticate a Bearer Authorization header."""
    if not value:
        return None
    scheme, separator, token = value.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token:
        return None
    return _principal_from_token(token.strip())


def authenticate(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Principal:
    """Authenticate a bearer token without revealing which credential failed."""
    middleware_principal = getattr(request.state, "principal", None)
    if isinstance(middleware_principal, Principal):
        return middleware_principal

    try:
        get_security_config()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured",
        ) from exc

    token = credentials.credentials if credentials else ""
    if credentials and credentials.scheme.lower() == "bearer":
        principal = _principal_from_token(token)
        if principal is not None:
            return principal

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_operator(principal: Principal = Depends(authenticate)) -> Principal:
    """Allow only the operator credential to access management data or actions."""
    if principal.role is not Role.OPERATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator permission required",
        )
    return principal


def require_device(principal: Principal = Depends(authenticate)) -> Principal:
    """Allow only the single local device principal to run liveness flows."""
    if principal.role is not Role.DEVICE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device permission required",
        )
    return principal


class ApiSecurityMiddleware:
    """Authenticate and authorize API calls before request bodies are consumed."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET").upper()
        is_api = path.startswith("/api/") or path == "/api"
        policy = get_api_policy(method, path) if is_api else None

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start" and is_api:
                enforced_headers = (
                    (b"cache-control", b"private, no-store"),
                    (b"pragma", b"no-cache"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"cross-origin-resource-policy", b"same-origin"),
                )
                enforced_names = {name for name, _ in enforced_headers}
                headers = [
                    (name, value)
                    for name, value in message.get("headers", ())
                    if name.lower() not in enforced_names
                ]
                headers.extend(enforced_headers)
                message["headers"] = headers
            await send(message)

        if is_api and method != "OPTIONS":
            if policy is None:
                await JSONResponse(
                    {"detail": "Not found"}, status_code=status.HTTP_404_NOT_FOUND
                )(scope, receive, send_with_security_headers)
                return

            if policy is not AccessPolicy.PUBLIC:
                try:
                    # Validate even when the header is absent. This preserves a
                    # clear fail-closed state if lifespan checks are bypassed by
                    # an alternate ASGI runner or a test harness.
                    get_security_config()
                    headers = {
                        key.decode("latin-1").lower(): value.decode("latin-1")
                        for key, value in scope.get("headers", ())
                    }
                    principal = principal_from_authorization_header(
                        headers.get("authorization")
                    )
                except RuntimeError:
                    await JSONResponse(
                        {"detail": "API authentication is not configured"},
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )(scope, receive, send_with_security_headers)
                    return

                if principal is None:
                    await JSONResponse(
                        {"detail": "Authentication required"},
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        headers={"WWW-Authenticate": "Bearer"},
                    )(scope, receive, send_with_security_headers)
                    return

                allowed = (
                    policy is AccessPolicy.AUTHENTICATED
                    or (policy is AccessPolicy.OPERATOR and principal.role is Role.OPERATOR)
                    or (policy is AccessPolicy.DEVICE and principal.role is Role.DEVICE)
                )
                if not allowed:
                    required_role = (
                        "Operator"
                        if policy is AccessPolicy.OPERATOR
                        else "Device"
                    )
                    await JSONResponse(
                        {"detail": f"{required_role} permission required"},
                        status_code=status.HTTP_403_FORBIDDEN,
                    )(scope, receive, send_with_security_headers)
                    return

                scope.setdefault("state", {})["principal"] = principal

        await self.app(scope, receive, send_with_security_headers)
