"""StegoHide header creation and validation."""

MAGIC_SIGNATURE = b"STEGOHIDE"
HEADER_SIZE_BYTES = len(MAGIC_SIGNATURE) + 4


def create_header(message_bytes):
    """Create the StegoHide header: magic + length + message bytes."""
    if message_bytes is None:
        message_bytes = b""
    message_length = len(message_bytes)
    if message_length > 0xFFFFFFFF:
        raise ValueError("Message too large for 32-bit length field.")

    length_bytes = message_length.to_bytes(4, byteorder="big", signed=False)
    return MAGIC_SIGNATURE + length_bytes + message_bytes


def parse_header(data):
    """Parse and validate a StegoHide header from the start of the data stream."""
    if len(data) < HEADER_SIZE_BYTES:
        raise ValueError("Header is too short.")

    magic = data[: len(MAGIC_SIGNATURE)]
    if magic != MAGIC_SIGNATURE:
        raise ValueError("Invalid StegoHide header.")

    length = int.from_bytes(data[len(MAGIC_SIGNATURE) : len(MAGIC_SIGNATURE) + 4], byteorder="big", signed=False)
    return {
        "magic": magic,
        "message_length": length,
        "header_size": HEADER_SIZE_BYTES,
    }
