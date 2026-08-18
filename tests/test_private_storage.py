"""Permission and minimization tests for local biometric storage."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.models.attendance_db import AttendanceDB
from backend.models.face_database import FaceDatabase


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
def test_face_store_repairs_modes_and_minimizes_images(tmp_path):
    old_umask = os.umask(0)
    try:
        db_path = tmp_path / "private-data" / "face_database.json"
        database = FaceDatabase(db_path=str(db_path))
        full_frame = np.random.default_rng(7).integers(
            0, 256, size=(720, 1280, 3), dtype=np.uint8
        )
        embedding = np.random.default_rng(8).normal(size=512)

        assert database.register_face(
            "person_safe", embedding, {"name": "Synthetic"}, full_frame
        )
        assert database.add_face_sample(
            "person_safe", embedding.copy(), full_frame
        )
    finally:
        os.umask(old_umask)

    assert mode(db_path.parent) == 0o700
    assert mode(db_path.parent / "embeddings") == 0o700
    assert mode(db_path.parent / "faces") == 0o700
    assert mode(db_path) == 0o600
    for path in (db_path.parent / "embeddings").glob("*.npy"):
        assert mode(path) == 0o600
    thumbnails = list((db_path.parent / "faces").glob("*.jpg"))
    assert len(thumbnails) == 1
    assert mode(thumbnails[0]) == 0o600
    stored_thumbnail = cv2.imread(str(thumbnails[0]))
    assert max(stored_thumbnail.shape[:2]) <= 256
    assert "db_path" not in database.get_statistics()


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
def test_attendance_database_is_private_under_permissive_umask(tmp_path):
    old_umask = os.umask(0)
    try:
        db_path = tmp_path / "attendance-data" / "attendance.db"
        attendance = AttendanceDB(db_path=str(db_path))
        assert attendance.record_attendance(
            "synthetic-face", "Synthetic", confidence=0.9
        )
    finally:
        os.umask(old_umask)

    assert mode(db_path.parent) == 0o700
    assert mode(db_path) == 0o600


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
def test_attendance_sidecars_are_repaired_and_symlinks_rejected(tmp_path):
    data_dir = tmp_path / "attendance-data"
    data_dir.mkdir()
    db_path = data_dir / "attendance.db"
    sidecar = data_dir / "attendance.db-wal"
    sidecar.write_bytes(b"synthetic-sidecar")
    sidecar.chmod(0o666)

    AttendanceDB(db_path=str(db_path))
    # SQLite may remove an orphaned WAL while opening; if it survives, it must
    # retain the repaired private mode.
    assert not sidecar.exists() or mode(sidecar) == 0o600

    outside = tmp_path / "outside.db"
    outside.write_bytes(b"ORIGINAL")
    linked_path = tmp_path / "linked-attendance" / "attendance.db"
    linked_path.parent.mkdir()
    try:
        linked_path.symlink_to(outside)
    except OSError:
        pytest.skip("Symbolic links are unavailable")
    with pytest.raises(RuntimeError, match="symbolic links"):
        AttendanceDB(db_path=str(linked_path))
    assert outside.read_bytes() == b"ORIGINAL"


def test_thumbnail_path_rejects_traversal_and_symlinks(tmp_path):
    db_path = tmp_path / "private-data" / "face_database.json"
    database = FaceDatabase(db_path=str(db_path))
    outside = tmp_path / "outside.jpg"
    assert cv2.imwrite(str(outside), np.zeros((8, 8, 3), dtype=np.uint8))

    database.faces["malicious"] = {
        "face_id": "malicious",
        "image_path": "../outside.jpg",
    }
    assert database.get_thumbnail_path("malicious") is None

    link = Path(database.faces_dir) / "linked.jpg"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symbolic links are unavailable")
    database.faces["linked"] = {
        "face_id": "linked",
        "image_path": "faces/linked.jpg",
    }
    assert database.get_thumbnail_path("linked") is None


def test_stale_symlinks_are_never_followed_by_biometric_writes(tmp_path):
    db_path = tmp_path / "private-data" / "face_database.json"
    database = FaceDatabase(db_path=str(db_path))
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"ORIGINAL")

    embedding_link = Path(database.embeddings_dir) / "person_safe.npy"
    try:
        embedding_link.symlink_to(outside)
    except OSError:
        pytest.skip("Symbolic links are unavailable")

    assert database.register_face(
        "person_safe", np.zeros(512), {"name": "Synthetic"}
    ) is False
    assert outside.read_bytes() == b"ORIGINAL"
    assert embedding_link.is_symlink()


def test_startup_rejects_links_in_private_biometric_tree(tmp_path):
    data_dir = tmp_path / "private-data"
    embeddings_dir = data_dir / "embeddings"
    faces_dir = data_dir / "faces"
    embeddings_dir.mkdir(parents=True)
    faces_dir.mkdir()
    outside = tmp_path / "outside.npy"
    outside.write_bytes(b"ORIGINAL")
    try:
        (embeddings_dir / "stale.npy").symlink_to(outside)
    except OSError:
        pytest.skip("Symbolic links are unavailable")

    with pytest.raises(RuntimeError, match="symbolic links"):
        FaceDatabase(db_path=str(data_dir / "face_database.json"))


def test_corrupt_existing_store_fails_closed(tmp_path):
    db_path = tmp_path / "private-data" / "face_database.json"
    db_path.parent.mkdir(parents=True)
    db_path.write_text("not-json", encoding="utf-8")
    database = FaceDatabase(db_path=str(db_path))

    assert database.register_face(
        "person_safe", np.zeros(512), {"name": "Synthetic"}
    ) is False
    assert db_path.read_text(encoding="utf-8") == "not-json"


def test_failed_artifact_deletion_remains_retryable(tmp_path, monkeypatch):
    db_path = tmp_path / "private-data" / "face_database.json"
    database = FaceDatabase(db_path=str(db_path))
    embedding = np.zeros(512)
    assert database.register_face(
        "person_safe",
        embedding,
        {"name": "Synthetic"},
        np.zeros((16, 16, 3), dtype=np.uint8),
    )

    real_remove = os.remove

    def fail_biometric_remove(path):
        if Path(path).suffix in {".npy", ".jpg"}:
            raise PermissionError("synthetic failure")
        return real_remove(path)

    monkeypatch.setattr(os, "remove", fail_biometric_remove)
    assert database.remove_face("person_safe") is False
    assert "person_safe" in database.faces

    monkeypatch.setattr(os, "remove", real_remove)
    assert database.remove_face("person_safe") is True
    assert "person_safe" not in database.faces
