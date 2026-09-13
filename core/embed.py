"""Embedding workflow for StegoHide."""

from core.bits import bytes_to_bits
from core.capacity import calculate_capacity
from core.header import create_header
from core.image import (
    embed_png_lsb,
    read_image,
    write_image,
)
from utils.errors import (
    InsufficientCapacityError,
    InvalidImageDataError,
)


def embed_message(message, source_path, output_path):
    """Embed a UTF-8 message into a PNG or BMP image."""

    if message is None:
        message = ""

    message_bytes = message.encode("utf-8")

    header = create_header(message_bytes)

    full_bits = bytes_to_bits(header)

    # Read only metadata first.
    #
    # This avoids decoding the complete image before
    # we know whether the message can fit.
    from core.image import read_image_metadata

    metadata = read_image_metadata(source_path)

    width = metadata["width"]
    height = metadata["height"]

    capacity_info = calculate_capacity(
        width,
        height,
    )

    if len(full_bits) > capacity_info["capacity_bits"]:
        raise InsufficientCapacityError(
            "The message is too large for the selected image."
        )

    source_suffix = str(source_path).lower()

    # Optimized PNG path.
    #
    # This avoids creating millions of Python pixel
    # objects and performs LSB embedding directly on
    # decoded PNG scanlines.
    if source_suffix.endswith(".png"):
        result = embed_png_lsb(
            source_path,
            output_path,
            full_bits,
        )

        if result["bits_embedded"] != len(full_bits):
            raise InvalidImageDataError(
                "Image data is corrupted or incomplete."
            )

        return {
            "output_path": output_path,
            "message_length": len(message_bytes),
            "capacity": capacity_info,
            "header_size": len(header),
        }

    # BMP fallback.
    image = read_image(source_path)

    pixels = image["pixels"]

    if len(pixels) == 0:
        raise InvalidImageDataError(
            "Image data is corrupted or incomplete."
        )

    bit_index = 0

    for pixel_index in range(len(pixels)):
        if bit_index >= len(full_bits):
            break

        pixel = list(pixels[pixel_index])

        for channel_index in range(3):
            if bit_index >= len(full_bits):
                break

            pixel[channel_index] = (
                pixel[channel_index] & 0xFE
            ) | full_bits[bit_index]

            bit_index += 1

        pixels[pixel_index] = tuple(pixel)

    if bit_index != len(full_bits):
        raise InvalidImageDataError(
            "Image data is corrupted or incomplete."
        )

    image["pixels"] = pixels

    write_image(
        output_path,
        image,
    )

    return {
        "output_path": output_path,
        "message_length": len(message_bytes),
        "capacity": capacity_info,
        "header_size": len(header),
    }