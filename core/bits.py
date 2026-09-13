"""Text and bit conversion utilities."""


def text_to_bits(text):
    """Convert UTF-8 text to a list of bits in big-endian order."""
    if text is None:
        text = ""
    data = text.encode("utf-8")
    bits = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def bits_to_text(bits):
    """Convert a list or string of bits to text."""
    if isinstance(bits, str):
        bits = [int(ch) for ch in bits if ch in "01"]

    if len(bits) % 8 != 0:
        raise ValueError("Bit stream length must be divisible by 8.")

    bytes_data = []
    for i in range(0, len(bits), 8):
        value = 0
        for bit in bits[i : i + 8]:
            value = (value << 1) | int(bit)
        bytes_data.append(value)

    return bytes(bytes_data).decode("utf-8")


def bits_to_bytes(bits):
    """Convert bits to a byte array."""
    if len(bits) % 8 != 0:
        raise ValueError("Bit stream length must be divisible by 8.")

    result = []
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i : i + 8]:
            byte = (byte << 1) | int(bit)
        result.append(byte)
    return bytes(result)


def bytes_to_bits(data):
    """Convert a byte sequence to a list of bits."""
    bits = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits
