"""Validation helpers used across StegoHide."""

import os
from pathlib import Path

from utils.errors import UnsupportedImageFormatError

SUPPORTED_EXTENSIONS = {".png", ".bmp"}


def validate_image_format(path):
    """Validate the image format and return the lower-case extension."""
    if not path:
        raise ValueError("No image path was provided.")

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    extension = file_path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedImageFormatError(
            "Unsupported image format. Supported formats: PNG, BMP."
        )
    return extension


def get_image_name(path):
    """Return just the file name from the path."""
    return os.path.basename(path)
