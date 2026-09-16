"""Image forensic analysis utilities for StegoHide."""

from pathlib import Path

from core.image import (
    read_image_metadata,
    extract_png_lsb,
)
from core.bits import bits_to_bytes
from forensics.hashing import calculate_sha256
from core.header import MAGIC_SIGNATURE, HEADER_SIZE_BYTES


def analyze_image(image_path):
    """
    Collect basic forensic information about an image.
    """

    path = Path(image_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {image_path}")

    metadata = read_image_metadata(path)

    width = metadata["width"]
    height = metadata["height"]

    pixel_count = width * height

    capacity_bits = pixel_count * 3
    capacity_bytes = capacity_bits // 8

    file_size_bytes = path.stat().st_size

    result = {
        "file_name": path.name,
        "file_path": str(path.resolve()),
        "file_size_bytes": file_size_bytes,
        "format": path.suffix.upper().lstrip("."),
        "width": width,
        "height": height,
        "pixel_count": pixel_count,
        "capacity_bits": capacity_bits,
        "capacity_bytes": capacity_bytes,
        "sha256": calculate_sha256(path),
    }

    return result
def check_stegohide_signature(image_path):
    """
    Quickly check whether the image contains
    the StegoHide signature.
    """

    path = Path(image_path)

    if path.suffix.lower() != ".png":
        return {
            "detected": False,
            "reason": "Signature check currently supports PNG."
        }

    required_bits = len(MAGIC_SIGNATURE) * 8

    bits = extract_png_lsb(
        path,
        required_bits,
    )

    if len(bits) < required_bits:
        return {
            "detected": False,
            "reason": "Not enough data for a StegoHide signature."
        }

    extracted = bits_to_bytes(bits)

    if extracted == MAGIC_SIGNATURE:
        return {
            "detected": True,
            "signature": MAGIC_SIGNATURE.decode("ascii"),
        }

    return {
        "detected": False,
        "signature": MAGIC_SIGNATURE.decode("ascii"),
    }

def fast_forensics(image_path):
    """
    Perform a fast forensic scan.

    The fast scan collects metadata, SHA-256,
    and checks for the StegoHide signature.
    """

    result = analyze_image(image_path)

    signature_result = check_stegohide_signature(
        image_path
    )

    result["stegohide_signature"] = signature_result

    return result

def format_forensics_report(result):
    """
    Format forensic analysis results for terminal display.
    """

    signature = result["stegohide_signature"]

    if signature["detected"]:
        signature_status = "DETECTED"
    else:
        signature_status = "NOT DETECTED"

    lines = [
        "========================================",
        "        StegoHide Image Forensics",
        "========================================",
        "",
        f"File Name            : {result['file_name']}",
        f"Format               : {result['format']}",
        f"Dimensions           : {result['width']} x {result['height']}",
        f"Pixel Count          : {result['pixel_count']}",
        f"File Size            : {result['file_size_bytes']} bytes",
        f"LSB Capacity         : {result['capacity_bytes']} bytes",
        "",
        "SHA-256",
        "----------------------------------------",
        result["sha256"],
        "",
        "StegoHide Signature",
        "----------------------------------------",
        signature_status,
    ]

    if signature["detected"]:
        lines.append(
            f"Signature            : {signature['signature']}"
        )

    lines.extend(
        [
            "",
            "Scan Type            : FAST",
            "========================================",
        ]
    )

    return "\n".join(lines)