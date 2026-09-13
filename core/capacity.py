"""Image capacity calculation and validation."""

HEADER_SIZE_BYTES = 13
HEADER_SIZE_BITS = HEADER_SIZE_BYTES * 8


def calculate_capacity(width, height):
    """Return available bits, bytes, and pixel count for the image."""
    if width <= 0 or height <= 0:
        raise ValueError("Image width and height must be positive integers.")

    pixels = width * height
    capacity_bits = pixels * 3
    capacity_bytes = capacity_bits // 8
    return {
        "width": width,
        "height": height,
        "pixels": pixels,
        "capacity_bits": capacity_bits,
        "capacity_bytes": capacity_bytes,
    }


def check_capacity(message_length, width, height):
    """Validate whether the image can store the required header + message data."""
    capacity = calculate_capacity(width, height)
    required_bits = HEADER_SIZE_BITS + (message_length * 8)
    return {
        "available_bits": capacity["capacity_bits"],
        "required_bits": required_bits,
        "sufficient": required_bits <= capacity["capacity_bits"],
        "capacity": capacity,
    }
