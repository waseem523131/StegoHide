"""File hashing utilities for StegoHide."""

import hashlib
from pathlib import Path


def calculate_sha256(file_path):
    """
    Calculate the SHA-256 hash of a file.

    Args:
        file_path: Path to the file.

    Returns:
        SHA-256 hash as a hexadecimal string.
    """
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()