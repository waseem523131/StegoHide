"""Extraction workflow for StegoHide."""

from pathlib import Path

from core.bits import bits_to_bytes
from core.header import HEADER_SIZE_BYTES, MAGIC_SIGNATURE
from core.image import (
    extract_png_lsb,
    read_image,
    read_image_metadata,
)
from utils.errors import (
    CorruptedDataError,
    InvalidMessageLengthError,
    NoStegoMessageFoundError,
)


def _bits_to_bytes(bits):
    """Convert complete groups of eight bits into bytes."""
    return bits_to_bytes(bits)


def _extract_bits_from_rgb_pixels(pixels, number_of_bits):
    """
    Extract LSB bits from RGB pixels.

    Supports:
        - list of RGB tuples: [(R,G,B), ...]
        - flat RGB bytearray: RGBRGBRGB...
    """
    bits = []

    if not pixels:
        return bits

    # BMP: [(R,G,B), ...]
    if isinstance(pixels[0], tuple):
        for pixel in pixels:
            if len(bits) >= number_of_bits:
                break

            r, g, b = pixel

            for channel in (r, g, b):
                if len(bits) >= number_of_bits:
                    break

                bits.append(channel & 1)

        return bits

    # Flat RGB data
    limit = min(number_of_bits, len(pixels))

    for index in range(limit):
        bits.append(pixels[index] & 1)

    return bits


def _extract_png_message(image_path):
    """
    Extract a StegoHide message using the optimized PNG path.
    """

    # ---------------------------------------------------------
    # Step 1: Extract the fixed StegoHide header
    # ---------------------------------------------------------

    required_header_bits = HEADER_SIZE_BYTES * 8

    extracted_bits = extract_png_lsb(
        image_path,
        required_header_bits,
    )

    if len(extracted_bits) < required_header_bits:
        raise NoStegoMessageFoundError(
            "No StegoHide message found."
        )

    header_bytes = _bits_to_bytes(
        extracted_bits
    )

    # ---------------------------------------------------------
    # Step 2: Validate the magic signature
    # ---------------------------------------------------------

    if (
        header_bytes[:len(MAGIC_SIGNATURE)]
        != MAGIC_SIGNATURE
    ):
        raise NoStegoMessageFoundError(
            "No StegoHide message found."
        )

    # ---------------------------------------------------------
    # Step 3: Read the message length
    # ---------------------------------------------------------

    length_start = len(MAGIC_SIGNATURE)
    length_end = length_start + 4

    message_length = int.from_bytes(
        header_bytes[length_start:length_end],
        byteorder="big",
        signed=False,
    )

    # ---------------------------------------------------------
    # Step 4: Validate message length against capacity
    # ---------------------------------------------------------

    metadata = read_image_metadata(
        image_path
    )

    capacity_bits = (
        metadata["width"]
        * metadata["height"]
        * 3
    )

    required_bits = (
        required_header_bits
        + message_length * 8
    )

    if required_bits > capacity_bits:
        raise InvalidMessageLengthError(
            "Embedded message length exceeds image capacity."
        )

    # ---------------------------------------------------------
    # Step 5: Extract header + message
    # ---------------------------------------------------------

    all_bits = extract_png_lsb(
        image_path,
        required_bits,
    )

    if len(all_bits) < required_bits:
        raise CorruptedDataError(
            "Image data is corrupted or incomplete."
        )

    # ---------------------------------------------------------
    # Step 6: Extract only the message payload
    # ---------------------------------------------------------

    payload_start = required_header_bits
    payload_end = required_bits

    payload_bits = all_bits[
        payload_start:payload_end
    ]

    if len(payload_bits) != message_length * 8:
        raise CorruptedDataError(
            "Image data is corrupted or incomplete."
        )

    payload_bytes = _bits_to_bytes(
        payload_bits
    )

    # ---------------------------------------------------------
    # Step 7: Decode UTF-8
    # ---------------------------------------------------------

    try:
        message = payload_bytes.decode(
            "utf-8"
        )

    except UnicodeDecodeError as exc:
        raise CorruptedDataError(
            "Hidden message is not valid UTF-8 data."
        ) from exc

    return {
        "message": message,
        "message_length": len(payload_bytes),
    }


def _extract_bmp_message(image_path):
    """
    Extract a StegoHide message using the existing BMP path.
    """

    image = read_image(
        image_path
    )

    pixels = image["pixels"]

    if not pixels:
        raise CorruptedDataError(
            "Image data is corrupted or incomplete."
        )

    # ---------------------------------------------------------
    # Step 1: Extract the fixed StegoHide header
    # ---------------------------------------------------------

    required_header_bits = HEADER_SIZE_BYTES * 8

    extracted_bits = _extract_bits_from_rgb_pixels(
        pixels,
        required_header_bits,
    )

    if len(extracted_bits) < required_header_bits:
        raise NoStegoMessageFoundError(
            "No StegoHide message found."
        )

    header_bytes = _bits_to_bytes(
        extracted_bits
    )

    # ---------------------------------------------------------
    # Step 2: Validate the magic signature
    # ---------------------------------------------------------

    if (
        header_bytes[:len(MAGIC_SIGNATURE)]
        != MAGIC_SIGNATURE
    ):
        raise NoStegoMessageFoundError(
            "No StegoHide message found."
        )

    # ---------------------------------------------------------
    # Step 3: Read the message length
    # ---------------------------------------------------------

    length_start = len(MAGIC_SIGNATURE)
    length_end = length_start + 4

    message_length = int.from_bytes(
        header_bytes[length_start:length_end],
        byteorder="big",
        signed=False,
    )

    # ---------------------------------------------------------
    # Step 4: Validate message length
    # ---------------------------------------------------------

    capacity_bits = (
        image["width"]
        * image["height"]
        * 3
    )

    required_bits = (
        required_header_bits
        + message_length * 8
    )

    if required_bits > capacity_bits:
        raise InvalidMessageLengthError(
            "Embedded message length exceeds image capacity."
        )

    # ---------------------------------------------------------
    # Step 5: Extract header + message
    # ---------------------------------------------------------

    all_bits = _extract_bits_from_rgb_pixels(
        pixels,
        required_bits,
    )

    if len(all_bits) < required_bits:
        raise CorruptedDataError(
            "Image data is corrupted or incomplete."
        )

    # ---------------------------------------------------------
    # Step 6: Extract only the message payload
    # ---------------------------------------------------------

    payload_start = required_header_bits
    payload_end = required_bits

    payload_bits = all_bits[
        payload_start:payload_end
    ]

    if len(payload_bits) != message_length * 8:
        raise CorruptedDataError(
            "Image data is corrupted or incomplete."
        )

    payload_bytes = _bits_to_bytes(
        payload_bits
    )

    # ---------------------------------------------------------
    # Step 7: Decode UTF-8
    # ---------------------------------------------------------

    try:
        message = payload_bytes.decode(
            "utf-8"
        )

    except UnicodeDecodeError as exc:
        raise CorruptedDataError(
            "Hidden message is not valid UTF-8 data."
        ) from exc

    return {
        "message": message,
        "message_length": len(payload_bytes),
    }


def extract_message(image_path):
    """
    Extract a hidden UTF-8 message from a PNG or BMP image.

    PNG uses the optimized direct LSB extraction path.
    BMP uses the existing pixel-based extraction path.
    """

    suffix = Path(
        image_path
    ).suffix.lower()

    if suffix == ".png":
        return _extract_png_message(
            image_path
        )

    return _extract_bmp_message(
        image_path
    )