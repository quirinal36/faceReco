"""Server-side client for the Edu Manager student and attendance API.

No biometric image, embedding, face identifier, or local access token is sent
to this service.  The integration only sends an already selected enrollment ID,
the date, and the configured attendance cell value.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import httpx


class EduManagerError(RuntimeError):
    """A non-sensitive failure while talking to Edu Manager."""


class EduManagerClient:
    def __init__(self) -> None:
        base_url = os.getenv("EDU_MANAGER_API_BASE_URL", "").strip().rstrip("/")
        api_key = os.getenv("EDU_MANAGER_API_KEY", "").strip()
        if not base_url.startswith("https://"):
            raise EduManagerError("Edu Manager API must use an HTTPS URL")
        if not api_key:
            raise EduManagerError("Edu Manager API credential is not configured")
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                timeout=httpx.Timeout(5.0, connect=3.0),
                **kwargs,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise EduManagerError("Edu Manager request failed") from error
        if not isinstance(payload, dict) or "data" not in payload:
            raise EduManagerError("Edu Manager returned an invalid response")
        return payload["data"]

    def list_students(self, *, query: str = "", page: int = 1, page_size: int = 50) -> dict[str, Any]:
        params = {"page": page, "page_size": min(max(page_size, 1), 200), "status": "active"}
        if query:
            params["q"] = query
        return self._request("GET", "/api/v1/students", params=params)

    def get_student(self, student_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/students/{student_id}")

    def list_monthly_enrollments(self, month: str) -> dict[str, Any]:
        return self._request("GET", "/api/v1/monthly-enrollments", params={"month": month})

    def put_attendance(self, enrollment_id: str, attendance_date: str, value: str) -> None:
        self._request(
            "PUT",
            f"/api/v1/monthly-enrollments/{enrollment_id}/attendances/{attendance_date}",
            json={"value": value},
        )


@lru_cache(maxsize=1)
def get_edu_manager_client() -> EduManagerClient:
    return EduManagerClient()
