"""Helpers for keeping biometric and attendance files private on local storage."""

from __future__ import annotations

import os
from pathlib import Path


PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


def ensure_private_directory(path: str | os.PathLike[str]) -> Path:
    """Create a directory and remove group/other access on POSIX systems."""
    directory = Path(path)
    if directory.is_symlink():
        raise RuntimeError("Private storage directories cannot be symbolic links")

    directory.mkdir(mode=PRIVATE_DIRECTORY_MODE, parents=True, exist_ok=True)
    if os.name == "posix":
        directory.chmod(PRIVATE_DIRECTORY_MODE)
    return directory


def ensure_private_file(path: str | os.PathLike[str]) -> Path:
    """Remove group/other access from an existing private file."""
    file_path = Path(path)
    if file_path.is_symlink():
        raise RuntimeError("Private storage files cannot be symbolic links")
    if not file_path.is_file():
        raise RuntimeError("Private storage path must be a regular file")
    if os.name == "posix":
        file_path.chmod(PRIVATE_FILE_MODE)
    return file_path
