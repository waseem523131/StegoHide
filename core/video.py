"""Raw video utilities for StegoHide."""

from pathlib import Path
import struct
from core.header import (
    create_header,
    parse_header,
)


# StegoHide Video format signature
VIDEO_MAGIC = b"STV1"

# Header:
# 4 bytes  -> magic
# 4 bytes  -> width
# 4 bytes  -> height
# 4 bytes  -> number of frames
# 1 byte   -> color channels (RGB = 3)
VIDEO_HEADER_FORMAT = ">4sIIIB"

VIDEO_HEADER_SIZE = struct.calcsize(
    VIDEO_HEADER_FORMAT
)


def create_video_header(
    width,
    height,
    frame_count,
):
    """Create the StegoHide video header."""

    if width <= 0:
        raise ValueError(
            "Width must be greater than zero."
        )

    if height <= 0:
        raise ValueError(
            "Height must be greater than zero."
        )

    if frame_count <= 0:
        raise ValueError(
            "Frame count must be greater than zero."
        )

    return struct.pack(
        VIDEO_HEADER_FORMAT,
        VIDEO_MAGIC,
        width,
        height,
        frame_count,
        3,
    )


def parse_video_header(data):
    """Read and validate a StegoHide video header."""

    if len(data) < VIDEO_HEADER_SIZE:
        raise ValueError(
            "Video header is too short."
        )

    (
        magic,
        width,
        height,
        frame_count,
        channels,
    ) = struct.unpack(
        VIDEO_HEADER_FORMAT,
        data[:VIDEO_HEADER_SIZE],
    )

    if magic != VIDEO_MAGIC:
        raise ValueError(
            "Invalid StegoHide video file."
        )

    if channels != 3:
        raise ValueError(
            "Only RGB video is supported."
        )

    return {
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "channels": channels,
        "header_size": VIDEO_HEADER_SIZE,
    }


def calculate_frame_size(width, height):
    """Calculate the size of one RGB frame in bytes."""

    if width <= 0 or height <= 0:
        raise ValueError(
            "Invalid video dimensions."
        )

    return width * height * 3


def calculate_video_capacity(
    width,
    height,
    frame_count,
):
    """
    Calculate the LSB capacity of a raw RGB video.

    One RGB byte provides one LSB bit.
    """

    frame_size = calculate_frame_size(
        width,
        height,
    )

    total_bytes = (
        frame_size * frame_count
    )

    capacity_bits = total_bytes

    capacity_bytes = (
        capacity_bits // 8
    )

    return {
        "frame_size": frame_size,
        "total_bytes": total_bytes,
        "capacity_bits": capacity_bits,
        "capacity_bytes": capacity_bytes,
    }
    
    
def create_stv_video(
    output_path,
    width,
    height,
    frames,
):
    """
    Create a StegoHide raw video file.

    Each frame must contain raw RGB bytes.
    """

    output_path = Path(output_path)

    frame_size = calculate_frame_size(
        width,
        height,
    )

    frame_count = len(frames)

    if frame_count == 0:
        raise ValueError(
            "At least one frame is required."
        )

    header = create_video_header(
        width,
        height,
        frame_count,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open("wb") as file:

        # Write video header
        file.write(header)

        # Write frames
        for index, frame in enumerate(frames):

            if len(frame) != frame_size:
                raise ValueError(
                    f"Invalid frame size at frame {index}."
                )

            file.write(frame)

    return {
        "output_path": str(output_path),
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "frame_size": frame_size,
    }


def read_stv_video(input_path):
    """
    Read a StegoHide raw video file.

    Returns the video information and RGB frames.
    """

    input_path = Path(input_path)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"File not found: {input_path}"
        )

    if input_path.suffix.lower() != ".stv":
        raise ValueError(
            "Only STV video files are supported."
        )

    with input_path.open("rb") as file:

        # Read header
        header_data = file.read(
            VIDEO_HEADER_SIZE
        )

        header = parse_video_header(
            header_data
        )

        frame_size = calculate_frame_size(
            header["width"],
            header["height"],
        )

        frames = []

        for index in range(
            header["frame_count"]
        ):

            frame = file.read(
                frame_size
            )

            if len(frame) != frame_size:
                raise ValueError(
                    f"Unexpected end of video at frame {index}."
                )

            frames.append(frame)

    return {
        "width": header["width"],
        "height": header["height"],
        "frame_count": header["frame_count"],
        "channels": header["channels"],
        "frame_size": frame_size,
        "frames": frames,
    }
    
def embed_bits_in_frames(frames, bits):
    """
    Embed binary bits into the LSB of RGB frame bytes.

    Bits are embedded sequentially:
    Frame 1 -> Frame 2 -> Frame 3 -> ...
    """

    total_capacity = sum(
        len(frame)
        for frame in frames
    )

    if len(bits) > total_capacity:
        raise ValueError(
            "Message is too large for video capacity."
        )

    modified_frames = [
        bytearray(frame)
        for frame in frames
    ]

    bit_index = 0

    for frame in modified_frames:

        for byte_index in range(len(frame)):

            if bit_index >= len(bits):
                return [
                    bytes(frame)
                    for frame in modified_frames
                ]

            bit = bits[bit_index]

            # Clear the LSB
            frame[byte_index] &= 0b11111110

            # Put the message bit into the LSB
            frame[byte_index] |= bit

            bit_index += 1

    return [
        bytes(frame)
        for frame in modified_frames
    ]


def extract_bits_from_frames(
    frames,
    number_of_bits,
):
    """
    Extract binary bits from the LSB
    of RGB frame bytes.
    """

    total_capacity = sum(
        len(frame)
        for frame in frames
    )

    if number_of_bits > total_capacity:
        raise ValueError(
            "Requested data exceeds video capacity."
        )

    bits = []

    for frame in frames:

        for byte in frame:

            if len(bits) >= number_of_bits:
                return bits

            bits.append(
                byte & 1
            )

    return bits

def _bits_to_bytes(bits):
    """Convert a list of bits into bytes."""

    if len(bits) % 8 != 0:
        raise ValueError(
            "Bit data is not aligned to bytes."
        )

    result = bytearray()

    for index in range(0, len(bits), 8):

        byte_value = 0

        for bit in bits[index:index + 8]:
            byte_value = (
                byte_value << 1
            ) | bit

        result.append(byte_value)

    return bytes(result)


def _bytes_to_bits(data):
    """Convert bytes into a list of bits."""

    bits = []

    for byte in data:

        for bit_position in range(7, -1, -1):

            bit = (
                byte >> bit_position
            ) & 1

            bits.append(bit)

    return bits


def hide_message_in_video(
    message,
    input_path,
    output_path,
):
    """
    Hide a UTF-8 message inside an STV video.
    """

    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"File not found: {input_path}"
        )

    if input_path.suffix.lower() != ".stv":
        raise ValueError(
            "Only STV video files are supported."
        )

    if output_path.resolve() == input_path.resolve():
        raise ValueError(
            "Output video must be different "
            "from input video."
        )

    # Read original video
    video = read_stv_video(
        input_path
    )

    # Convert message to UTF-8
    message_bytes = message.encode(
        "utf-8"
    )

    # Create StegoHide payload
    payload = create_header(
        message_bytes
    )

    # Convert payload to bits
    bits = _bytes_to_bits(
        payload
    )

    # Check capacity
    capacity = calculate_video_capacity(
        video["width"],
        video["height"],
        video["frame_count"],
    )

    if len(bits) > capacity["capacity_bits"]:
        raise ValueError(
            "Message is too large for video capacity."
        )

    # Embed bits into frames
    modified_frames = embed_bits_in_frames(
        video["frames"],
        bits,
    )

    # Create output video
    result = create_stv_video(
        output_path,
        video["width"],
        video["height"],
        modified_frames,
    )

    return {
        "output_path": result["output_path"],
        "message_length": len(message_bytes),
        "capacity_bytes": capacity["capacity_bytes"],
        "required_bits": len(bits),
    }


def extract_message_from_video(
    input_path,
):
    """
    Extract a StegoHide message from an STV video.
    """

    input_path = Path(input_path)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"File not found: {input_path}"
        )

    if input_path.suffix.lower() != ".stv":
        raise ValueError(
            "Only STV video files are supported."
        )

    # Read video
    video = read_stv_video(
        input_path
    )

    # First extract enough bits for the
    # fixed StegoHide header.
    header_bits_count = (
        13 * 8
    )

    header_bits = extract_bits_from_frames(
        video["frames"],
        header_bits_count,
    )

    header_data = _bits_to_bytes(
        header_bits
    )

    # Parse StegoHide header
    header = parse_header(
        header_data
    )

    # Calculate complete payload size
    total_payload_bytes = (
        header["header_size"]
        + header["message_length"]
    )

    total_payload_bits = (
        total_payload_bytes * 8
    )

    # Extract complete payload
    payload_bits = extract_bits_from_frames(
        video["frames"],
        total_payload_bits,
    )

    payload = _bits_to_bytes(
        payload_bits
    )

    # Extract message
    message_start = header["header_size"]

    message_end = (
        message_start
        + header["message_length"]
    )

    if len(payload) < message_end:
        raise ValueError(
            "Invalid message length or corrupted data."
        )

    message_bytes = payload[
        message_start:message_end
    ]

    try:

        message = message_bytes.decode(
            "utf-8"
        )

    except UnicodeDecodeError as exc:

        raise ValueError(
            "Hidden data is not valid UTF-8."
        ) from exc

    return {
        "message": message,
        "message_length": header[
            "message_length"
        ],
    }
    
    
def save_frame_as_bmp(
    frame,
    width,
    height,
    output_path,
):
    """
    Save one RGB frame as an uncompressed BMP image.
    No external libraries are required.
    """

    output_path = Path(output_path)

    expected_size = (
        width * height * 3
    )

    if len(frame) != expected_size:
        raise ValueError(
            "Invalid RGB frame size."
        )

    # BMP rows must be aligned to 4 bytes.
    row_size = width * 3
    padding_size = (
        4 - (row_size % 4)
    ) % 4

    padded_row_size = (
        row_size + padding_size
    )

    pixel_data_size = (
        padded_row_size * height
    )

    file_size = (
        14 + 40 + pixel_data_size
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open("wb") as file:

        # =========================
        # BMP File Header
        # =========================

        file.write(b"BM")

        file.write(
            struct.pack(
                "<I",
                file_size,
            )
        )

        file.write(
            struct.pack(
                "<HH",
                0,
                0,
            )
        )

        file.write(
            struct.pack(
                "<I",
                54,
            )
        )

        # =========================
        # DIB Header
        # =========================

        file.write(
            struct.pack(
                "<I",
                40,
            )
        )

        file.write(
            struct.pack(
                "<i",
                width,
            )
        )

        file.write(
            struct.pack(
                "<i",
                -height,
            )
        )

        file.write(
            struct.pack(
                "<H",
                1,
            )
        )

        file.write(
            struct.pack(
                "<H",
                24,
            )
        )

        file.write(
            struct.pack(
                "<I",
                0,
            )
        )

        file.write(
            struct.pack(
                "<I",
                pixel_data_size,
            )
        )

        file.write(
            struct.pack(
                "<i",
                2835,
            )
        )

        file.write(
            struct.pack(
                "<i",
                2835,
            )
        )

        file.write(
            struct.pack(
                "<I",
                0,
            )
        )

        file.write(
            struct.pack(
                "<I",
                0,
            )
        )

        # =========================
        # Pixel Data
        # =========================

        padding = b"\x00" * padding_size

        for row in range(height):

            start = (
                row * width * 3
            )

            end = (
                start + width * 3
            )

            rgb_row = frame[
                start:end
            ]

            # BMP uses BGR order.
            bgr_row = bytearray()

            for index in range(
                0,
                len(rgb_row),
                3,
            ):
                red = rgb_row[index]
                green = rgb_row[index + 1]
                blue = rgb_row[index + 2]

                bgr_row.extend(
                    [
                        blue,
                        green,
                        red,
                    ]
                )

            file.write(bgr_row)
            file.write(padding)

    return str(output_path)

def preview_stv_frame(
    input_path,
    output_path,
    frame_index=0,
):
    """
    Export one STV frame as a BMP image.
    """

    video = read_stv_video(
        input_path
    )

    if frame_index < 0:
        raise ValueError(
            "Frame index cannot be negative."
        )

    if frame_index >= video["frame_count"]:
        raise ValueError(
            "Frame index is outside the video."
        )

    frame = video["frames"][
        frame_index
    ]

    return save_frame_as_bmp(
        frame,
        video["width"],
        video["height"],
        output_path,
    )
    
def create_demo_frame(width, height, frame_index):
    """
    Create a simple visible RGB frame
    using only the Python Standard Library.
    """

    frame = bytearray()

    for y in range(height):
        for x in range(width):

            red = (
                x * 255 // max(width - 1, 1)
            )

            green = (
                y * 255 // max(height - 1, 1)
            )

            blue = (
                (frame_index * 40) % 256
            )

            frame.extend(
                [red, green, blue]
            )

    return bytes(frame)

def create_demo_video(
    output_path,
    width=160,
    height=120,
    frame_count=10,
):
    """
    Create a visible demonstration STV video.
    """

    frames = []

    for frame_index in range(frame_count):

        frame = create_demo_frame(
            width,
            height,
            frame_index,
        )

        frames.append(frame)

    return create_stv_video(
        output_path,
        width,
        height,
        frames,
    )
    
    
def create_moving_demo_frame(
    width,
    height,
    frame_index,
    frame_count,
):
    """
    Create one RGB frame with a moving rectangle.

    This uses only the Python Standard Library.
    """

    frame = bytearray(
        width * height * 3
    )

    # Rectangle size
    rectangle_width = width // 5
    rectangle_height = height // 5

    # Calculate horizontal position
    max_x = width - rectangle_width

    if frame_count <= 1:
        x_position = 0
    else:
        x_position = (
            frame_index * max_x
            // (frame_count - 1)
        )

    # Vertical position
    y_position = (
        height - rectangle_height
    ) // 2

    for y in range(height):

        for x in range(width):

            index = (
                (y * width + x) * 3
            )

            # Background
            red = (
                x * 255
                // max(width - 1, 1)
            )

            green = (
                y * 255
                // max(height - 1, 1)
            )

            blue = 80

            # Moving rectangle
            if (
                x_position
                <= x
                < x_position + rectangle_width
                and
                y_position
                <= y
                < y_position + rectangle_height
            ):
                red = 255
                green = 255
                blue = 255

            frame[index] = red
            frame[index + 1] = green
            frame[index + 2] = blue

    return bytes(frame)

def create_moving_demo_video(
    output_path,
    width=160,
    height=120,
    frame_count=20,
):
    """
    Create a moving demonstration video
    in the StegoHide STV format.
    """

    if frame_count <= 0:
        raise ValueError(
            "Frame count must be greater than zero."
        )

    frames = []

    for frame_index in range(frame_count):

        frame = create_moving_demo_frame(
            width,
            height,
            frame_index,
            frame_count,
        )

        frames.append(frame)

    return create_stv_video(
        output_path,
        width,
        height,
        frames,
    )
    
def hide_message_in_video(
    message,
    input_path,
    output_path,
):
    """
    Hide a UTF-8 message inside an STV video
    using LSB steganography.
    """

    from core.header import create_header

    input_path = Path(input_path)
    output_path = Path(output_path)

    # Read the source video
    video = read_stv_video(input_path)

    frames = video["frames"]

    # Convert message to UTF-8 bytes
    message_bytes = message.encode("utf-8")

    # Create StegoHide header + message
    payload = create_header(message_bytes)

    # Convert bytes to bits
    bits = []

    for byte in payload:

        for bit_position in range(7, -1, -1):

            bits.append(
                (byte >> bit_position) & 1
            )

    # Embed the bits into video frames
    modified_frames = embed_bits_in_frames(
        frames,
        bits,
    )

    # Create the output STV video
    result = create_stv_video(
        output_path=output_path,
        width=video["width"],
        height=video["height"],
        frames=modified_frames,
    )

    return {
        "output_path": result["output_path"],
        "width": result["width"],
        "height": result["height"],
        "frame_count": result["frame_count"],
        "message_length": len(message_bytes),
        "payload_length": len(payload),
        "embedded_bits": len(bits),
    }
    
def extract_message_from_video(input_path):
    """
    Extract a hidden UTF-8 message from an STV video.
    """

    from core.header import (
        MAGIC_SIGNATURE,
        HEADER_SIZE_BYTES,
        parse_header,
    )

    input_path = Path(input_path)

    # Read the video
    video = read_stv_video(input_path)

    frames = video["frames"]

    # We first need enough bits for the fixed header
    header_bits = extract_bits_from_frames(
        frames,
        HEADER_SIZE_BYTES * 8,
    )

    # Convert header bits to bytes
    header_bytes = bytearray()

    for index in range(
        0,
        len(header_bits),
        8,
    ):

        byte_value = 0

        for bit in header_bits[index:index + 8]:
            byte_value = (
                (byte_value << 1)
                | bit
            )

        header_bytes.append(byte_value)

    # Parse and validate StegoHide header
    header = parse_header(
        bytes(header_bytes)
    )

    message_length = header["message_length"]

    # Total payload = header + message
    total_bytes = (
        HEADER_SIZE_BYTES
        + message_length
    )

    total_bits = total_bytes * 8

    # Extract the complete payload
    payload_bits = extract_bits_from_frames(
        frames,
        total_bits,
    )

    # Convert bits back to bytes
    payload = bytearray()

    for index in range(
        0,
        len(payload_bits),
        8,
    ):

        byte_value = 0

        for bit in payload_bits[index:index + 8]:
            byte_value = (
                (byte_value << 1)
                | bit
            )

        payload.append(byte_value)

    payload = bytes(payload)

    # Parse header again from the complete payload
    parsed_header = parse_header(
        payload
    )

    message_start = parsed_header["header_size"]

    message_end = (
        message_start
        + parsed_header["message_length"]
    )

    message_bytes = payload[
        message_start:message_end
    ]

    # Decode UTF-8
    message = message_bytes.decode(
        "utf-8"
    )

    return {
        "input_path": str(input_path),
        "width": video["width"],
        "height": video["height"],
        "frame_count": video["frame_count"],
        "message_length": len(message_bytes),
        "message": message,
    }