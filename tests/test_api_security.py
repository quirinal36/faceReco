"""Regression tests for the local edge API security boundary."""

from __future__ import annotations

import importlib
import os
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

OPERATOR_TOKEN = "operator-token-" + "a" * 40
DEVICE_TOKEN = "device-token-" + "b" * 40


@pytest.fixture(autouse=True)
def configured_security(monkeypatch):
    monkeypatch.setenv("FACERECO_OPERATOR_TOKEN", OPERATOR_TOKEN)
    monkeypatch.setenv("FACERECO_DEVICE_TOKEN", DEVICE_TOKEN)
    monkeypatch.setenv("FACERECO_ENV", "development")
    monkeypatch.delenv("FACERECO_OPERATOR_TOKEN_FILE", raising=False)
    monkeypatch.delenv("FACERECO_DEVICE_TOKEN_FILE", raising=False)
    monkeypatch.delenv("FACERECO_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("FACERECO_BIND_HOST", raising=False)
    monkeypatch.delenv("FACERECO_ALLOW_NON_LOOPBACK", raising=False)

    security = importlib.import_module("security")
    security.get_security_config.cache_clear()
    yield
    security.get_security_config.cache_clear()


@pytest.fixture
def client():
    server = importlib.import_module("server")
    return TestClient(server.app, base_url="http://127.0.0.1")


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_tokens_are_required_distinct_and_long(monkeypatch):
    security = importlib.import_module("security")

    monkeypatch.delenv("FACERECO_OPERATOR_TOKEN")
    security.get_security_config.cache_clear()
    with pytest.raises(RuntimeError):
        security.get_security_config()

    monkeypatch.setenv("FACERECO_OPERATOR_TOKEN", DEVICE_TOKEN)
    security.get_security_config.cache_clear()
    with pytest.raises(RuntimeError):
        security.get_security_config()


def test_production_requires_encrypted_storage_attestation(monkeypatch):
    security = importlib.import_module("security")
    monkeypatch.setenv("FACERECO_ENV", "production")
    monkeypatch.delenv("FACERECO_ENCRYPTED_STORAGE_VERIFIED", raising=False)
    security.get_security_config.cache_clear()
    with pytest.raises(RuntimeError, match="encrypted storage"):
        security.get_security_config()


def test_unknown_environment_fails_closed_everywhere(monkeypatch):
    security = importlib.import_module("security")
    server = importlib.import_module("server")
    model_module = importlib.import_module("models.face_recognition")

    monkeypatch.setenv("FACERECO_ENV", "prodction")
    security.get_security_config.cache_clear()

    with pytest.raises(RuntimeError, match="FACERECO_ENV"):
        security.get_security_config()
    with pytest.raises(RuntimeError, match="FACERECO_ENV"):
        server.get_bind_host()
    with pytest.raises(RuntimeError, match="FACERECO_ENV"):
        model_module.validate_model_artifacts()


def test_production_requires_file_backed_credentials(monkeypatch, tmp_path):
    security = importlib.import_module("security")

    monkeypatch.setenv("FACERECO_ENV", "production")
    monkeypatch.setenv("FACERECO_ENCRYPTED_STORAGE_VERIFIED", "true")
    security.get_security_config.cache_clear()

    with pytest.raises(RuntimeError, match="file-backed"):
        security.get_security_config()

    operator_file = tmp_path / "operator.token"
    device_file = tmp_path / "device.token"
    operator_file.write_text(OPERATOR_TOKEN, encoding="utf-8")
    device_file.write_text(DEVICE_TOKEN, encoding="utf-8")
    operator_file.chmod(0o600)
    device_file.chmod(0o600)
    monkeypatch.delenv("FACERECO_OPERATOR_TOKEN")
    monkeypatch.delenv("FACERECO_DEVICE_TOKEN")
    monkeypatch.setenv("FACERECO_OPERATOR_TOKEN_FILE", str(operator_file))
    monkeypatch.setenv("FACERECO_DEVICE_TOKEN_FILE", str(device_file))
    security.get_security_config.cache_clear()

    assert security.get_security_config().environment == "production"


def test_auth_runs_before_validation_and_role_checks(client):
    missing = client.post("/api/face/register")
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert "no-store" in missing.headers["cache-control"]

    wrong_role = client.post(
        "/api/face/register", headers=bearer(DEVICE_TOKEN)
    )
    assert wrong_role.status_code == 403

    # An authorized caller reaches FastAPI's request validation. Override the
    # heavyweight dependencies because this test must never load a model/store.
    server = importlib.import_module("server")
    routes = importlib.import_module("api.routes")
    server.app.dependency_overrides[routes.get_face_recognizer] = object
    server.app.dependency_overrides[routes.get_face_database] = object
    try:
        authorized = client.post(
            "/api/face/register", headers=bearer(OPERATOR_TOKEN)
        )
        assert authorized.status_code == 422
        assert authorized.json() == {"detail": "Invalid request"}
    finally:
        server.app.dependency_overrides.clear()


def test_upload_body_limit_precedes_multipart_and_dependencies(
    client, monkeypatch
):
    server = importlib.import_module("server")
    routes = importlib.import_module("api.routes")
    upload_limits = importlib.import_module("utils.upload_limits")
    formparsers = importlib.import_module("starlette.formparsers")

    async def forbidden_parse(_self):
        raise AssertionError("multipart parser must not run for oversized bodies")

    def forbidden_dependency():
        raise AssertionError("route dependencies must not run for oversized bodies")

    monkeypatch.setattr(formparsers.MultiPartParser, "parse", forbidden_parse)
    server.app.dependency_overrides[routes.get_face_recognizer] = forbidden_dependency
    server.app.dependency_overrides[routes.get_face_database] = forbidden_dependency
    oversized_bytes = b"x" * upload_limits.MAX_UPLOAD_BODY_BYTES
    try:
        unauthenticated = client.post(
            "/api/face/register",
            data={"name": "Synthetic User"},
            files={
                "file": ("synthetic.jpg", oversized_bytes, "image/jpeg")
            },
        )
        response = client.post(
            "/api/face/register",
            headers=bearer(OPERATOR_TOKEN),
            data={"name": "Synthetic User"},
            files={
                "file": ("synthetic.jpg", oversized_bytes, "image/jpeg")
            },
        )
    finally:
        server.app.dependency_overrides.clear()

    assert unauthenticated.status_code == 401
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body is too large"}


def test_accepted_uploads_never_roll_to_os_temp(client, monkeypatch):
    server = importlib.import_module("server")
    routes = importlib.import_module("api.routes")
    rolled_to_disk = None

    async def inspect_upload(file):
        nonlocal rolled_to_disk
        rolled_to_disk = file.file._rolled
        return np.zeros((8, 8, 3), dtype=np.uint8)

    monkeypatch.setattr(routes, "_read_image", inspect_upload)
    monkeypatch.setattr(routes, "_extract_enrollment_sample", lambda *_args: None)
    server.app.dependency_overrides[routes.get_face_recognizer] = object
    server.app.dependency_overrides[routes.get_face_database] = object
    try:
        response = client.post(
            "/api/face/register",
            headers=bearer(OPERATOR_TOKEN),
            data={"name": "Synthetic User"},
            files={
                "file": (
                    "synthetic.jpg",
                    b"x" * (2 * 1024 * 1024),
                    "image/jpeg",
                )
            },
        )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert rolled_to_disk is False


def test_chunked_upload_without_length_is_rejected(client):
    response = client.post(
        "/api/face/register",
        headers={
            **bearer(OPERATOR_TOKEN),
            "Content-Type": "multipart/form-data; boundary=synthetic",
        },
        content=iter([b"--synthetic--\r\n"]),
    )
    assert response.status_code == 411


def test_role_separation_and_whoami(client):
    operator = client.get(
        "/api/auth/whoami", headers=bearer(OPERATOR_TOKEN)
    )
    device = client.get("/api/auth/whoami", headers=bearer(DEVICE_TOKEN))
    assert operator.json() == {"role": "operator"}
    assert device.json() == {"role": "device"}

    assert client.post(
        "/api/liveness/start", headers=bearer(OPERATOR_TOKEN)
    ).status_code == 403
    assert client.get(
        "/api/faces/list", headers=bearer(DEVICE_TOKEN)
    ).status_code == 403


def test_health_is_public_and_minimal(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert "db_path" not in response.text
    assert "no-store" in response.headers["cache-control"]


@pytest.mark.parametrize(
    "path",
    [
        "/data/faces/person.jpg",
        "/data/embeddings/person.npy",
        "/data/face_database.json",
        "/data/attendance.db",
        "/data/attendance.db-wal",
        "/data/attendance.db-journal",
    ],
)
def test_old_data_mount_is_gone(client, path):
    assert client.get(path).status_code == 404
    assert client.get(path, headers=bearer(OPERATOR_TOKEN)).status_code == 404
    assert client.head(path).status_code == 404


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/face/register"),
        ("DELETE", "/api/face/sample"),
        ("DELETE", "/api/attendance/1"),
        ("GET", "/api/camera/stream"),
    ],
)
def test_sensitive_operator_endpoints_reject_anonymous_and_device(
    client, method, path
):
    anonymous = client.request(method, path)
    assert anonymous.status_code == 401
    assert client.request(
        method, path, headers=bearer(DEVICE_TOKEN)
    ).status_code == 403


def test_query_and_invalid_tokens_are_ignored_without_echo_or_logs(client, caplog):
    caplog.clear()
    query_token = client.get(f"/api/faces/list?token={OPERATOR_TOKEN}")
    invalid_token = "invalid-credential-that-must-not-be-logged"
    invalid = client.get(
        "/api/faces/list", headers=bearer(invalid_token)
    )

    assert query_token.status_code == 401
    assert invalid.status_code == 401
    assert OPERATOR_TOKEN not in query_token.text
    assert invalid_token not in invalid.text
    assert OPERATOR_TOKEN not in caplog.text
    assert invalid_token not in caplog.text


def test_unconfigured_auth_fails_closed_before_dependencies(
    client, monkeypatch
):
    security = importlib.import_module("security")
    server = importlib.import_module("server")
    routes = importlib.import_module("api.routes")
    called = False

    def forbidden_dependency():
        nonlocal called
        called = True
        raise AssertionError("dependency must not run")

    server.app.dependency_overrides[routes.get_face_database] = forbidden_dependency
    monkeypatch.delenv("FACERECO_OPERATOR_TOKEN")
    monkeypatch.delenv("FACERECO_DEVICE_TOKEN")
    security.get_security_config.cache_clear()
    try:
        response = client.get("/api/faces/list")
        assert response.status_code == 503
        assert response.json() == {
            "detail": "API authentication is not configured"
        }
        assert called is False
    finally:
        server.app.dependency_overrides.clear()


def test_internal_failures_are_generic_and_do_not_log_sensitive_values(
    client, caplog
):
    sensitive_value = "Synthetic Person /private/biometrics/store.json"

    class FailingDatabase:
        def get_all_faces(self):
            raise RuntimeError(sensitive_value)

    server = importlib.import_module("server")
    routes = importlib.import_module("api.routes")
    server.app.dependency_overrides[routes.get_face_database] = FailingDatabase
    caplog.set_level("ERROR")
    try:
        response = client.get(
            "/api/faces/list", headers=bearer(OPERATOR_TOKEN)
        )
        assert response.status_code == 500
        assert response.json() == {"detail": "Request could not be completed"}
        assert sensitive_value not in response.text
        assert sensitive_value not in caplog.text
        assert "face_list_failed" in caplog.text
    finally:
        server.app.dependency_overrides.clear()


def test_failed_face_artifact_deletion_returns_retryable_server_error(client):
    class FailingRemovalDatabase:
        faces = {"sample": {"face_id": "sample"}}

        def remove_face(self, _face_id):
            return False

    server = importlib.import_module("server")
    routes = importlib.import_module("api.routes")
    server.app.dependency_overrides[routes.get_face_database] = (
        FailingRemovalDatabase
    )
    try:
        response = client.delete(
            "/api/face/sample", headers=bearer(OPERATOR_TOKEN)
        )
        assert response.status_code == 500
        assert response.json() == {"detail": "Request could not be completed"}
    finally:
        server.app.dependency_overrides.clear()


def test_cors_uses_exact_allowlist(client):
    preflight_headers = {
        "Origin": "https://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    allowed = client.options("/api/face/register", headers=preflight_headers)
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://localhost:5173"
    assert allowed.headers["access-control-allow-origin"] != "*"

    for origin in ("https://localhost:5173.evil.test", "null"):
        rejected = client.options(
            "/api/face/register",
            headers={**preflight_headers, "Origin": origin},
        )
        assert "access-control-allow-origin" not in rejected.headers


def test_wildcard_cors_configuration_is_rejected(monkeypatch):
    security = importlib.import_module("security")
    monkeypatch.setenv("FACERECO_CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="Wildcard"):
        security.get_cors_origins()


def test_thumbnail_requires_operator_and_reencodes(client, tmp_path):
    source = np.random.default_rng(1).integers(
        0, 256, size=(720, 1280, 3), dtype=np.uint8
    )
    source_path = tmp_path / "source.jpg"
    assert cv2.imwrite(str(source_path), source)
    source_bytes = source_path.read_bytes()

    class ThumbnailDatabase:
        def get_thumbnail_path(self, face_id):
            return str(source_path) if face_id == "known" else None

    server = importlib.import_module("server")
    routes = importlib.import_module("api.routes")
    server.app.dependency_overrides[routes.get_face_database] = ThumbnailDatabase
    try:
        assert client.get("/api/faces/known/thumbnail").status_code == 401
        assert client.get(
            "/api/faces/known/thumbnail", headers=bearer(DEVICE_TOKEN)
        ).status_code == 403

        response = client.get(
            "/api/faces/known/thumbnail", headers=bearer(OPERATOR_TOKEN)
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert "no-store" in response.headers["cache-control"]
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["cross-origin-resource-policy"] == "same-origin"
        assert response.content != source_bytes
        decoded = cv2.imdecode(
            np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR
        )
        assert max(decoded.shape[:2]) <= 256
    finally:
        server.app.dependency_overrides.clear()


def test_every_api_route_has_an_explicit_policy():
    security = importlib.import_module("security")
    server = importlib.import_module("server")

    uncovered = []
    for route in server.app.routes:
        if not getattr(route, "path", "").startswith("/api/"):
            continue
        sample_path = re.sub(r"\{[^}]+\}", "sample", route.path)
        for method in route.methods - {"HEAD", "OPTIONS"}:
            if security.get_api_policy(method, sample_path) is None:
                uncovered.append(f"{method} {route.path}")
    assert uncovered == []


def test_listener_defaults_loopback_and_production_rejects_public(monkeypatch):
    server = importlib.import_module("server")
    assert server.get_bind_host() == "127.0.0.1"

    monkeypatch.setenv("FACERECO_BIND_HOST", "0.0.0.0")
    with pytest.raises(RuntimeError):
        server.get_bind_host()

    monkeypatch.setenv("FACERECO_ALLOW_NON_LOOPBACK", "true")
    with pytest.raises(RuntimeError, match="explicit local or private interface"):
        server.get_bind_host()

    for public_address in ("8.8.8.8", "2001:4860:4860::8888"):
        monkeypatch.setenv("FACERECO_BIND_HOST", public_address)
        with pytest.raises(RuntimeError, match="local or private"):
            server.get_bind_host()

    monkeypatch.setenv("FACERECO_ENV", "production")
    with pytest.raises(RuntimeError, match="loopback"):
        monkeypatch.setenv("FACERECO_BIND_HOST", "192.0.2.10")
        server.get_bind_host()


def test_request_listener_boundary_blocks_alternate_wildcard_launch():
    server = importlib.import_module("server")
    external_interface = TestClient(
        server.app, base_url="http://192.168.50.10"
    )
    response = external_interface.get("/api/health")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}

    loopback_interface = TestClient(
        server.app, base_url="http://127.0.0.1"
    )
    assert loopback_interface.get("/api/health").status_code == 200


def test_production_model_bundle_must_be_preprovisioned(monkeypatch, tmp_path):
    model_module = importlib.import_module("models.face_recognition")
    monkeypatch.setenv("FACERECO_ENV", "production")
    monkeypatch.setenv("FACERECO_MODEL_ROOT", str(tmp_path))

    with pytest.raises(RuntimeError, match="provisioned"):
        model_module.validate_model_artifacts()

    bundle = tmp_path / "models" / "buffalo_l"
    bundle.mkdir(parents=True)
    (bundle / "detector.onnx").write_bytes(b"synthetic-test-model")
    assert model_module.validate_model_artifacts() == tmp_path

    monkeypatch.setenv("FACERECO_MODEL_NAME", "../escape")
    with pytest.raises(RuntimeError, match="invalid"):
        model_module.validate_model_artifacts()


def test_lifespan_audits_face_store_before_serving(monkeypatch):
    server = importlib.import_module("server")
    face_store_checked = False

    class BrokenFaceStore:
        is_available = False

    def broken_face_store():
        nonlocal face_store_checked
        face_store_checked = True
        return BrokenFaceStore()

    monkeypatch.setattr(server, "get_face_database", broken_face_store)
    monkeypatch.setattr(server, "get_attendance_db", object)

    with pytest.raises(RuntimeError, match="loaded safely"):
        with TestClient(server.app):
            pass
    assert face_store_checked is True


def test_invalid_liveness_session_is_rejected_before_biometric_work(
    client, monkeypatch
):
    server = importlib.import_module("server")
    routes = importlib.import_module("api.routes")
    biometric_work_called = False

    class MissingSessionDetector:
        def get_session(self, _session_id, owner_id=None):
            assert owner_id == "local-device"
            return None

    def forbidden_biometric_dependency():
        nonlocal biometric_work_called
        biometric_work_called = True
        raise AssertionError("biometric work must not run")

    server.app.dependency_overrides[routes.get_liveness_detector] = (
        MissingSessionDetector
    )
    monkeypatch.setattr(
        routes, "get_face_recognizer", forbidden_biometric_dependency
    )
    monkeypatch.setattr(
        routes, "get_face_database", forbidden_biometric_dependency
    )
    try:
        response = client.post(
            "/api/liveness/check",
            headers=bearer(DEVICE_TOKEN),
            data={"session_id": "invalid-or-foreign-session"},
            files={"file": ("frame.jpg", b"not-decoded", "image/jpeg")},
        )
        assert response.status_code == 404
        assert biometric_work_called is False
        assert "face_id" not in response.text
        assert "face_name" not in response.text
    finally:
        server.app.dependency_overrides.clear()


def test_active_liveness_check_does_not_disclose_identity(
    client, monkeypatch
):
    routes = importlib.import_module("api.routes")
    server = importlib.import_module("server")
    liveness_module = importlib.import_module("models.liveness")

    class ActiveSession:
        status = liveness_module.SessionStatus.ACTIVE

    class ActiveDetector:
        def get_session(self, _session_id, owner_id=None):
            assert owner_id == "local-device"
            return ActiveSession()

        def check_pose(self, **_kwargs):
            return {
                "challenge_passed": False,
                "session_completed": False,
                "message": "Continue",
            }

    class Recognizer:
        def detect_and_extract(self, _image):
            return [{"pose": [0.0, 0.0, 0.0], "embedding": np.zeros(512)}]

    class Database:
        faces = {
            "sensitive-id": {"metadata": {"name": "Sensitive Name"}}
        }

        def recognize_face(self, _embedding):
            return "sensitive-id", 0.99

    server.app.dependency_overrides[routes.get_liveness_detector] = ActiveDetector
    monkeypatch.setattr(routes, "get_face_recognizer", Recognizer)
    monkeypatch.setattr(routes, "get_face_database", Database)
    encoded, frame = cv2.imencode(".jpg", np.zeros((8, 8, 3), dtype=np.uint8))
    assert encoded
    try:
        response = client.post(
            "/api/liveness/check",
            headers=bearer(DEVICE_TOKEN),
            data={"session_id": "valid-active-session"},
            files={"file": ("frame.jpg", frame.tobytes(), "image/jpeg")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["session_completed"] is False
        assert body["face_id"] is None
        assert body["face_name"] is None
        assert body["face_confidence"] is None
        assert "Sensitive Name" not in response.text
        assert "sensitive-id" not in response.text
    finally:
        server.app.dependency_overrides.clear()


def test_liveness_state_is_rechecked_after_upload_read(client, monkeypatch):
    routes = importlib.import_module("api.routes")
    server = importlib.import_module("server")
    liveness_module = importlib.import_module("models.liveness")
    biometric_work_called = False

    class Session:
        def __init__(self, status):
            self.status = status

    class CompletingDetector:
        calls = 0

        def get_session(self, _session_id, owner_id=None):
            assert owner_id == "local-device"
            self.calls += 1
            status = (
                liveness_module.SessionStatus.ACTIVE
                if self.calls == 1
                else liveness_module.SessionStatus.COMPLETED
            )
            return Session(status)

    def forbidden_biometric_dependency():
        nonlocal biometric_work_called
        biometric_work_called = True
        raise AssertionError("terminal session must not run biometric work")

    server.app.dependency_overrides[routes.get_liveness_detector] = (
        CompletingDetector
    )
    monkeypatch.setattr(
        routes, "get_face_recognizer", forbidden_biometric_dependency
    )
    monkeypatch.setattr(
        routes, "get_face_database", forbidden_biometric_dependency
    )
    encoded, frame = cv2.imencode(".jpg", np.zeros((8, 8, 3), dtype=np.uint8))
    assert encoded
    try:
        response = client.post(
            "/api/liveness/check",
            headers=bearer(DEVICE_TOKEN),
            data={"session_id": "just-completed-session"},
            files={"file": ("frame.jpg", frame.tobytes(), "image/jpeg")},
        )
        assert response.status_code == 409
        assert biometric_work_called is False
        assert "face_id" not in response.text
        assert "face_name" not in response.text
    finally:
        server.app.dependency_overrides.clear()


def test_liveness_status_hides_identity_until_completion(client):
    routes = importlib.import_module("api.routes")
    server = importlib.import_module("server")
    liveness_module = importlib.import_module("models.liveness")
    detector = liveness_module.LivenessDetector()
    session, error = detector.create_session(client_id="local-device")
    assert error is None
    session.face_id = "sensitive-id"
    session.face_name = "Sensitive Name"

    server.app.dependency_overrides[routes.get_liveness_detector] = lambda: detector
    try:
        active = client.post(
            "/api/liveness/status",
            headers=bearer(DEVICE_TOKEN),
            json={"session_id": session.session_id},
        )
        assert active.status_code == 200
        assert active.json()["face_id"] is None
        assert active.json()["face_name"] is None
        assert "Sensitive Name" not in active.text

        session.status = liveness_module.SessionStatus.COMPLETED
        completed = client.post(
            "/api/liveness/status",
            headers=bearer(DEVICE_TOKEN),
            json={"session_id": session.session_id},
        )
        assert completed.status_code == 200
        assert completed.json()["face_id"] == "sensitive-id"
        assert completed.json()["face_name"] == "Sensitive Name"
    finally:
        server.app.dependency_overrides.clear()
