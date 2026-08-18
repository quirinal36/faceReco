"""Contract tests for the server-side Edu Manager client."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))

from integrations.edu_manager import EduManagerClient, EduManagerError


def configured_client(monkeypatch) -> EduManagerClient:
    monkeypatch.setenv("EDU_MANAGER_API_BASE_URL", "https://edu-manager-api.example")
    monkeypatch.setenv("EDU_MANAGER_API_KEY", "test-rest-api-key")
    return EduManagerClient()


def test_student_requests_use_server_bearer_credential(monkeypatch):
    client = configured_client(monkeypatch)
    captured = {}

    def request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return httpx.Response(200, json={"data": {"data": [], "meta": {"total_count": 0}}})

    monkeypatch.setattr(httpx, "request", request)
    assert client.list_students(query="Kim") == {"data": [], "meta": {"total_count": 0}}
    assert captured["method"] == "GET"
    assert captured["url"].endswith("/api/v1/students")
    assert captured["headers"] == {"Authorization": "Bearer test-rest-api-key"}
    assert captured["params"]["q"] == "Kim"


def test_attendance_put_only_sends_enrollment_date_and_value(monkeypatch):
    client = configured_client(monkeypatch)
    captured = {}

    def request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return httpx.Response(200, json={"data": {"date": "2026-08-18", "value": "출석"}})

    monkeypatch.setattr(httpx, "request", request)
    client.put_attendance("enrollment-1", "2026-08-18", "출석")
    assert captured["method"] == "PUT"
    assert captured["url"].endswith("/attendances/2026-08-18")
    assert captured["json"] == {"value": "출석"}


def test_client_rejects_missing_or_insecure_configuration(monkeypatch):
    monkeypatch.delenv("EDU_MANAGER_API_BASE_URL", raising=False)
    monkeypatch.delenv("EDU_MANAGER_API_KEY", raising=False)
    with pytest.raises(EduManagerError):
        EduManagerClient()

    monkeypatch.setenv("EDU_MANAGER_API_BASE_URL", "http://insecure.example")
    monkeypatch.setenv("EDU_MANAGER_API_KEY", "test-rest-api-key")
    with pytest.raises(EduManagerError):
        EduManagerClient()
