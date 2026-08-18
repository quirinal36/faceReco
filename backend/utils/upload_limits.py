"""In-memory request limits for biometric image uploads."""

from __future__ import annotations

import re
from collections import deque

from starlette.formparsers import MultiPartParser
from starlette.responses import JSONResponse


MAX_IMAGE_BYTES = 5 * 1024 * 1024
# Leave bounded room for multipart headers and the short name/session fields.
MAX_UPLOAD_BODY_BYTES = MAX_IMAGE_BYTES + 64 * 1024

_UPLOAD_PATHS = (
    re.compile(r"^/api/face/register$"),
    re.compile(r"^/api/face/[^/]+/add-sample$"),
    re.compile(r"^/api/liveness/check$"),
)


def _is_upload_request(scope) -> bool:
    path = scope.get("path", "")
    return scope.get("method", "GET").upper() == "POST" and any(
        pattern.fullmatch(path) for pattern in _UPLOAD_PATHS
    )


def configure_multipart_memory_limit() -> None:
    """Keep every accepted upload part in memory instead of the OS temp path."""
    if not hasattr(MultiPartParser, "spool_max_size"):
        raise RuntimeError("Installed Starlette cannot enforce private upload spooling")
    # A file part cannot be larger than the already bounded whole request.
    MultiPartParser.spool_max_size = MAX_UPLOAD_BODY_BYTES + 1


class UploadBodyLimitMiddleware:
    """Authenticate first, then buffer and cap multipart bodies before parsing.

    Buffering at this ASGI layer prevents Starlette from opening a temporary
    file before the route-level image check runs. Requiring Content-Length also
    rejects unbounded chunked upload streams.
    """

    def __init__(self, app, max_body_bytes: int = MAX_UPLOAD_BODY_BYTES):
        self.app = app
        self.max_body_bytes = max_body_bytes

    @staticmethod
    async def _reject(scope, receive, send, status_code: int, detail: str) -> None:
        response = JSONResponse({"detail": detail}, status_code=status_code)
        await response(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not _is_upload_request(scope):
            await self.app(scope, receive, send)
            return

        content_lengths = [
            value.decode("latin-1").strip()
            for name, value in scope.get("headers", ())
            if name.decode("latin-1").lower() == "content-length"
        ]
        if not content_lengths:
            await self._reject(scope, receive, send, 411, "Content-Length required")
            return
        if len(content_lengths) != 1:
            await self._reject(scope, receive, send, 400, "Invalid request body")
            return

        try:
            declared_length = int(content_lengths[0], 10)
        except ValueError:
            declared_length = -1
        if declared_length < 0:
            await self._reject(scope, receive, send, 400, "Invalid request body")
            return
        if declared_length > self.max_body_bytes:
            await self._reject(scope, receive, send, 413, "Request body is too large")
            return

        chunks = deque()
        actual_length = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                await self._reject(scope, receive, send, 400, "Invalid request body")
                return
            if message["type"] != "http.request":
                continue

            body = message.get("body", b"")
            actual_length += len(body)
            if actual_length > self.max_body_bytes:
                await self._reject(scope, receive, send, 413, "Request body is too large")
                return
            if body:
                chunks.append(body)
            if not message.get("more_body", False):
                break

        if actual_length != declared_length:
            await self._reject(scope, receive, send, 400, "Invalid request body")
            return

        async def replay_receive():
            if chunks:
                body = chunks.popleft()
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": bool(chunks),
                }
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)
