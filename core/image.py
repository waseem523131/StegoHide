"""Manual PNG and BMP image parsing and writing using the Standard Library."""

import struct
import zlib
from pathlib import Path

from utils.errors import InvalidImageDataError, UnsupportedImageFormatError


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
BMP_SIGNATURE = b"BM"


def validate_image(path):
    """Validate that the image path points to a supported PNG or BMP file."""
    if not path:
        raise ValueError("No image path was provided.")

    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    suffix = file_path.suffix.lower()

    if suffix not in {".png", ".bmp"}:
        raise UnsupportedImageFormatError(
            "Unsupported image format. Supported formats: PNG, BMP."
        )

    with open(file_path, "rb") as handle:
        header = handle.read(8)

    if suffix == ".png" and header != PNG_SIGNATURE:
        raise InvalidImageDataError("Invalid PNG signature.")

    if suffix == ".bmp" and header[:2] != BMP_SIGNATURE:
        raise InvalidImageDataError("Invalid BMP signature.")

    return suffix


def read_image_metadata(path):
    """Read only image metadata needed for capacity calculations."""
    suffix = validate_image(path)

    if suffix == ".png":
        with open(path, "rb") as handle:
            data = handle.read(33)

        if len(data) < 33 or data[:8] != PNG_SIGNATURE:
            raise InvalidImageDataError("Invalid PNG signature.")

        if data[12:16] != b"IHDR":
            raise InvalidImageDataError("PNG IHDR chunk is missing.")

        (
            width,
            height,
            bit_depth,
            color_type,
            compression,
            filter_method,
            interlace,
        ) = struct.unpack(">IIBBBBB", data[16:29])

        if width <= 0 or height <= 0:
            raise InvalidImageDataError(
                "PNG width and height must be positive."
            )

        if bit_depth != 8:
            raise UnsupportedImageFormatError(
                "Unsupported PNG bit depth. Only 8-bit PNG is supported."
            )

        if color_type not in (2, 6):
            raise UnsupportedImageFormatError(
                "Unsupported PNG color type. Only RGB and RGBA are supported."
            )

        if compression != 0 or filter_method != 0 or interlace != 0:
            raise UnsupportedImageFormatError(
                "Unsupported PNG features detected."
            )

        return {
            "format": "PNG",
            "width": width,
            "height": height,
            "channels": 3,
        }

    # BMP
    with open(path, "rb") as handle:
        data = handle.read(54)

    if len(data) < 54 or data[:2] != BMP_SIGNATURE:
        raise InvalidImageDataError("Invalid BMP signature.")

    dib_size = struct.unpack("<I", data[14:18])[0]

    if dib_size != 40:
        raise UnsupportedImageFormatError(
            "Unsupported BMP header size. Only BITMAPINFOHEADER is supported."
        )

    width, height = struct.unpack("<ii", data[18:26])

    if width <= 0 or height <= 0:
        raise InvalidImageDataError(
            "BMP width and height must be positive."
        )

    bit_count = struct.unpack("<H", data[28:30])[0]
    compression = struct.unpack("<I", data[30:34])[0]

    if bit_count != 24:
        raise UnsupportedImageFormatError(
            "Unsupported BMP bit depth. Only 24-bit BMP is supported."
        )

    if compression != 0:
        raise UnsupportedImageFormatError(
            "Unsupported BMP compression. Only uncompressed BMP is supported."
        )

    return {
        "format": "BMP",
        "width": width,
        "height": height,
        "channels": 3,
    }


def read_image(path):
    """Read a supported image and return a dictionary with pixel data."""
    suffix = validate_image(path)

    if suffix == ".png":
        return read_png_image(path)

    return read_bmp_image(path)


def write_image(path, image_data):
    """Write image data to a PNG or BMP file."""
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if suffix == ".png":
        write_png_image(file_path, image_data)

    elif suffix == ".bmp":
        write_bmp_image(file_path, image_data)

    else:
        raise UnsupportedImageFormatError(
            "Unsupported image format. Supported formats: PNG, BMP."
        )


def _paeth_predictor(left, above, upper_left):
    """PNG Paeth predictor."""
    p = left + above - upper_left

    pa = abs(p - left)
    pb = abs(p - above)
    pc = abs(p - upper_left)

    if pa <= pb and pa <= pc:
        return left

    if pb <= pc:
        return above

    return upper_left


def _decode_png_rows(raw, width, height, channels):
    """
    Decode PNG filtered rows into unfiltered RGB/RGBA rows.

    Returns:
        list[bytearray]: decoded rows.
    """
    bytes_per_pixel = channels
    stride = width * channels
    expected_raw_size = height * (1 + stride)

    if len(raw) != expected_raw_size:
        if len(raw) < expected_raw_size:
            raise InvalidImageDataError(
                "PNG pixel data is incomplete."
            )

        raise InvalidImageDataError(
            "PNG pixel data contains unexpected trailing bytes."
        )

    rows = []

    pos_raw = 0
    previous_row = bytearray(stride)

    for _ in range(height):
        filter_type = raw[pos_raw]
        pos_raw += 1

        filtered_row = raw[pos_raw:pos_raw + stride]
        pos_raw += stride

        row = bytearray(stride)

        if filter_type == 0:
            row[:] = filtered_row

        elif filter_type == 1:
            # Sub
            for i, value in enumerate(filtered_row):
                left = (
                    row[i - bytes_per_pixel]
                    if i >= bytes_per_pixel
                    else 0
                )

                row[i] = (value + left) & 0xFF

        elif filter_type == 2:
            # Up
            for i, value in enumerate(filtered_row):
                row[i] = (
                    value + previous_row[i]
                ) & 0xFF

        elif filter_type == 3:
            # Average
            for i, value in enumerate(filtered_row):
                left = (
                    row[i - bytes_per_pixel]
                    if i >= bytes_per_pixel
                    else 0
                )

                above = previous_row[i]

                row[i] = (
                    value + ((left + above) // 2)
                ) & 0xFF

        elif filter_type == 4:
            # Paeth
            for i, value in enumerate(filtered_row):
                left = (
                    row[i - bytes_per_pixel]
                    if i >= bytes_per_pixel
                    else 0
                )

                above = previous_row[i]

                upper_left = (
                    previous_row[i - bytes_per_pixel]
                    if i >= bytes_per_pixel
                    else 0
                )

                row[i] = (
                    value
                    + _paeth_predictor(
                        left,
                        above,
                        upper_left,
                    )
                ) & 0xFF

        else:
            raise UnsupportedImageFormatError(
                f"Unsupported PNG filter type: {filter_type}. "
                "Supported types: 0, 1, 2, 3, 4."
            )

        rows.append(row)
        previous_row = row

    return rows


def _parse_png(path):
    """
    Parse PNG structure and return metadata plus compressed IDAT data.
    """
    with open(path, "rb") as handle:
        data = handle.read()

    if len(data) < 8 or data[:8] != PNG_SIGNATURE:
        raise InvalidImageDataError("Invalid PNG signature.")

    pos = 8

    width = None
    height = None
    bit_depth = None
    color_type = None
    compression = None
    filter_method = None
    interlace = None

    idat_parts = []

    while pos + 8 <= len(data):
        length = struct.unpack(
            ">I",
            data[pos:pos + 4],
        )[0]

        chunk_type = data[pos + 4:pos + 8]

        chunk_end = pos + 12 + length

        if chunk_end > len(data):
            raise InvalidImageDataError(
                "PNG chunk extends beyond the file."
            )

        chunk_data = data[
            pos + 8:
            pos + 8 + length
        ]

        pos = chunk_end

        if chunk_type == b"IHDR":
            if length != 13:
                raise InvalidImageDataError(
                    "Malformed PNG IHDR chunk."
                )

            (
                width,
                height,
                bit_depth,
                color_type,
                compression,
                filter_method,
                interlace,
            ) = struct.unpack(
                ">IIBBBBB",
                chunk_data,
            )

            if width <= 0 or height <= 0:
                raise InvalidImageDataError(
                    "PNG width and height must be positive."
                )

            if bit_depth != 8:
                raise UnsupportedImageFormatError(
                    "Unsupported PNG bit depth. "
                    "Only 8-bit PNG is supported."
                )

            if color_type not in (2, 6):
                raise UnsupportedImageFormatError(
                    "Unsupported PNG color type. "
                    "Only RGB and RGBA are supported."
                )

            if (
                compression != 0
                or filter_method != 0
                or interlace != 0
            ):
                raise UnsupportedImageFormatError(
                    "Unsupported PNG features detected. "
                    "Only 8-bit, non-interlaced PNG files are supported."
                )

        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)

        elif chunk_type == b"IEND":
            break

    if (
        width is None
        or height is None
        or bit_depth is None
        or color_type is None
    ):
        raise InvalidImageDataError(
            "PNG image metadata is incomplete or invalid."
        )

    compressed = b"".join(idat_parts)

    try:
        raw = zlib.decompress(compressed)
    except zlib.error as exc:
        raise InvalidImageDataError(
            "PNG image data is corrupted or incomplete."
        ) from exc

    return {
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "color_type": color_type,
        "raw": raw,
    }


def read_png_image(path):
    """
    Read an 8-bit, non-interlaced RGB/RGBA PNG.

    Pixels are returned as RGB tuples:
        [(R,G,B), (R,G,B), ...]
    """
    png = _parse_png(path)

    width = png["width"]
    height = png["height"]
    color_type = png["color_type"]
    raw = png["raw"]

    channels = 4 if color_type == 6 else 3

    rows = _decode_png_rows(
        raw,
        width,
        height,
        channels,
    )

    pixels = []

    for row in rows:
        for i in range(0, len(row), channels):
            r = row[i]
            g = row[i + 1]
            b = row[i + 2]

            pixels.append((r, g, b))

    return {
        "format": "PNG",
        "width": width,
        "height": height,
        "channels": 3,
        "pixels": pixels,
        "color_type": color_type,
        "mode": "RGB" if color_type == 2 else "RGBA",
    }


def _make_png_chunk(chunk_type, chunk_data):
    """Create a PNG chunk."""
    crc = zlib.crc32(
        chunk_type + chunk_data
    ) & 0xFFFFFFFF

    return (
        struct.pack(">I", len(chunk_data))
        + chunk_type
        + chunk_data
        + struct.pack(">I", crc)
    )


def _write_png_raw(
    file_path,
    width,
    height,
    color_type,
    raw_data,
):
    """Write raw unfiltered PNG scanlines."""
    compressed = zlib.compress(
        bytes(raw_data),
        level=1,
    )

    ihdr = struct.pack(
        ">IIBBBBB",
        width,
        height,
        8,
        color_type,
        0,
        0,
        0,
    )

    png_bytes = (
        PNG_SIGNATURE
        + _make_png_chunk(b"IHDR", ihdr)
        + _make_png_chunk(b"IDAT", compressed)
        + _make_png_chunk(b"IEND", b"")
    )

    with open(file_path, "wb") as handle:
        handle.write(png_bytes)


def write_png_image(file_path, image_data):
    """Write image data as a valid PNG."""
    width = image_data["width"]
    height = image_data["height"]
    pixels = image_data["pixels"]

    color_type = image_data.get("color_type", 2)

    channels = 4 if color_type == 6 else 3

    stride = width * channels

    raw_data = bytearray()

    if isinstance(pixels, (bytes, bytearray)):
        row_size = width * 3

        for y in range(height):
            raw_data.append(0)

            start = y * row_size
            end = start + row_size

            rgb_row = pixels[start:end]

            if channels == 3:
                raw_data.extend(rgb_row)

            else:
                # RGB -> RGBA
                for x in range(width):
                    index = x * 3

                    raw_data.extend(
                        (
                            rgb_row[index],
                            rgb_row[index + 1],
                            rgb_row[index + 2],
                            255,
                        )
                    )

    else:
        for y in range(height):
            raw_data.append(0)

            row_start = y * width

            for x in range(width):
                r, g, b = pixels[row_start + x]

                raw_data.extend((r, g, b))

                if channels == 4:
                    raw_data.append(255)

    _write_png_raw(
        file_path,
        width,
        height,
        color_type,
        raw_data,
    )

def embed_png_lsb(
    source_path,
    output_path,
    bits,
):
    """
    Embed LSB bits directly into an 8-bit, non-interlaced PNG.

    Pixel order:
        Left -> Right
        Top -> Bottom

    Channel order:
        Red -> Green -> Blue

    The PNG is decoded row by row and only RGB channels are modified.
    """

    if not bits:
        raise ValueError("No bits were provided for embedding.")

    png = _parse_png(source_path)

    width = png["width"]
    height = png["height"]
    color_type = png["color_type"]
    raw = png["raw"]

    channels = 4 if color_type == 6 else 3
    stride = width * channels
    row_size = 1 + stride
    expected_raw_size = height * row_size

    if len(raw) != expected_raw_size:
        raise InvalidImageDataError(
            "PNG pixel data is incomplete or invalid."
        )

    total_capacity_bits = width * height * 3

    if len(bits) > total_capacity_bits:
        raise InvalidImageDataError(
            "The message exceeds the image capacity."
        )

    # Keep the complete PNG raw data.
    # We modify only the bytes that actually contain hidden data.
    output_raw = bytearray(raw)

    bit_index = 0
    previous_row = bytearray(stride)

    for y in range(height):
        raw_position = y * row_size

        filter_type = raw[raw_position]

        filtered_row = raw[
            raw_position + 1:
            raw_position + 1 + stride
        ]

        row = bytearray(stride)

        # ---------------------------------------------------------
        # Reconstruct the original row from the PNG filter.
        # ---------------------------------------------------------

        if filter_type == 0:
            row[:] = filtered_row

        elif filter_type == 1:
            for i, value in enumerate(filtered_row):
                left = (
                    row[i - channels]
                    if i >= channels
                    else 0
                )

                row[i] = (
                    value + left
                ) & 0xFF

        elif filter_type == 2:
            for i, value in enumerate(filtered_row):
                row[i] = (
                    value + previous_row[i]
                ) & 0xFF

        elif filter_type == 3:
            for i, value in enumerate(filtered_row):
                left = (
                    row[i - channels]
                    if i >= channels
                    else 0
                )

                above = previous_row[i]

                row[i] = (
                    value
                    + ((left + above) // 2)
                ) & 0xFF

        elif filter_type == 4:
            for i, value in enumerate(filtered_row):
                left = (
                    row[i - channels]
                    if i >= channels
                    else 0
                )

                above = previous_row[i]

                upper_left = (
                    previous_row[i - channels]
                    if i >= channels
                    else 0
                )

                row[i] = (
                    value
                    + _paeth_predictor(
                        left,
                        above,
                        upper_left,
                    )
                ) & 0xFF

        else:
            raise UnsupportedImageFormatError(
                f"Unsupported PNG filter type: {filter_type}. "
                "Supported types: 0, 1, 2, 3, 4."
            )

        # ---------------------------------------------------------
        # Embed bits only while there are bits remaining.
        # ---------------------------------------------------------

        if bit_index < len(bits):

            max_rgb_bytes = width * 3

            for rgb_index in range(max_rgb_bytes):

                if bit_index >= len(bits):
                    break

                pixel_index = rgb_index // 3
                channel_index = rgb_index % 3

                byte_index = (
                    pixel_index * channels
                    + channel_index
                )

                row[byte_index] = (
                    row[byte_index] & 0xFE
                ) | bits[bit_index]

                bit_index += 1

            # -----------------------------------------------------
            # Re-filter this modified row.
            #
            # We use filter type 0 for modified rows.
            # This makes the output row contain the actual RGB/RGBA
            # values directly.
            # -----------------------------------------------------

            output_raw[raw_position] = 0

            output_raw[
                raw_position + 1:
                raw_position + 1 + stride
            ] = row

        # ---------------------------------------------------------
        # If this row was not modified, keep its original PNG data.
        # ---------------------------------------------------------

        previous_row = row

        # Once all bits are embedded, no more rows need modification.
        # Their original filtered data remains untouched.
        if bit_index >= len(bits):
            break

    if bit_index != len(bits):
        raise InvalidImageDataError(
            "Failed to embed all message bits."
        )

    # -------------------------------------------------------------
    # Write the final PNG.
    # -------------------------------------------------------------

    _write_png_raw(
        output_path,
        width,
        height,
        color_type,
        output_raw,
    )

    return {
        "width": width,
        "height": height,
        "color_type": color_type,
        "channels": 3,
        "bits_embedded": bit_index,
    }

def extract_png_lsb(path, number_of_bits):
    """
    Extract LSB bits directly from a PNG image.

    This avoids creating a large Python pixel list.
    Pixel order:
        Left -> Right
        Top -> Bottom

    Channel order:
        Red -> Green -> Blue
    """
    if number_of_bits <= 0:
        return []

    png = _parse_png(path)

    width = png["width"]
    height = png["height"]
    color_type = png["color_type"]
    raw = png["raw"]

    channels = 4 if color_type == 6 else 3
    stride = width * channels

    expected_raw_size = height * (1 + stride)

    if len(raw) != expected_raw_size:
        raise InvalidImageDataError(
            "PNG pixel data is incomplete or invalid."
        )

    bits = []
    previous_row = bytearray(stride)
    raw_position = 0

    for y in range(height):
        filter_type = raw[raw_position]
        raw_position += 1

        filtered_row = raw[
            raw_position:
            raw_position + stride
        ]

        raw_position += stride

        row = bytearray(stride)

        if filter_type == 0:
            row[:] = filtered_row

        elif filter_type == 1:
            for i, value in enumerate(filtered_row):
                left = (
                    row[i - channels]
                    if i >= channels
                    else 0
                )
                row[i] = (value + left) & 0xFF

        elif filter_type == 2:
            for i, value in enumerate(filtered_row):
                row[i] = (
                    value + previous_row[i]
                ) & 0xFF

        elif filter_type == 3:
            for i, value in enumerate(filtered_row):
                left = (
                    row[i - channels]
                    if i >= channels
                    else 0
                )
                above = previous_row[i]

                row[i] = (
                    value
                    + ((left + above) // 2)
                ) & 0xFF

        elif filter_type == 4:
            for i, value in enumerate(filtered_row):
                left = (
                    row[i - channels]
                    if i >= channels
                    else 0
                )

                above = previous_row[i]

                upper_left = (
                    previous_row[i - channels]
                    if i >= channels
                    else 0
                )

                row[i] = (
                    value
                    + _paeth_predictor(
                        left,
                        above,
                        upper_left,
                    )
                ) & 0xFF

        else:
            raise UnsupportedImageFormatError(
                f"Unsupported PNG filter type: {filter_type}. "
                "Supported types: 0, 1, 2, 3, 4."
            )

        # Extract only RGB channels.
        for pixel_index in range(width):
            base = pixel_index * channels

            for channel_index in range(3):
                if len(bits) >= number_of_bits:
                    return bits

                bits.append(
                    row[base + channel_index] & 1
                )

        previous_row = row

    return bits

def read_bmp_image(path):
    """Read a supported 24-bit uncompressed BMP subset."""
    with open(path, "rb") as handle:
        data = handle.read()

    if len(data) < 14:
        raise InvalidImageDataError("BMP file is too short.")

    if data[:2] != BMP_SIGNATURE:
        raise InvalidImageDataError("Invalid BMP signature.")

    file_size, reserved1, reserved2, pixel_offset = struct.unpack(
        "<IHHI",
        data[2:14],
    )

    if file_size > len(data):
        raise InvalidImageDataError(
            "BMP file size exceeds actual file length."
        )

    if len(data) < 40 or pixel_offset < 14:
        raise InvalidImageDataError(
            "BMP header is incomplete."
        )

    dib_size = struct.unpack(
        "<I",
        data[14:18],
    )[0]

    if dib_size != 40:
        raise UnsupportedImageFormatError(
            "Unsupported BMP header size. "
            "Only BITMAPINFOHEADER is supported."
        )

    width, height = struct.unpack(
        "<ii",
        data[18:26],
    )

    if width <= 0 or height <= 0:
        raise InvalidImageDataError(
            "BMP width and height must be positive."
        )

    bit_count = struct.unpack(
        "<H",
        data[28:30],
    )[0]

    compression = struct.unpack(
        "<I",
        data[30:34],
    )[0]

    if bit_count != 24:
        raise UnsupportedImageFormatError(
            "Unsupported BMP bit depth. "
            "Only 24-bit BMP is supported."
        )

    if compression != 0:
        raise UnsupportedImageFormatError(
            "Unsupported BMP compression. "
            "Only uncompressed BMP is supported."
        )

    row_stride = ((width * 3) + 3) // 4 * 4

    expected_pixel_data_size = (
        row_stride * abs(height)
    )

    if (
        pixel_offset + expected_pixel_data_size
        > len(data)
    ):
        raise InvalidImageDataError(
            "BMP pixel data is incomplete."
        )

    pixel_data = data[
        pixel_offset:
        pixel_offset + expected_pixel_data_size
    ]

    pixels = []

    if height < 0:
        top_down = True
        height = abs(height)
    else:
        top_down = False

    for y in range(height):
        row_index = (   
            y
            if top_down
            else height - 1 - y
        )

        row_start = row_index * row_stride
        row_end = row_start + row_stride

        row = pixel_data[
            row_start:row_end
        ]

        for x in range(width):
            b = row[x * 3]
            g = row[x * 3 + 1]
            r = row[x * 3 + 2]

            pixels.append((r, g, b))

    return {
        "format": "BMP",
        "width": width,
        "height": height,
        "channels": 3,
        "pixels": pixels,
    }


def write_bmp_image(file_path, image_data):
    """Write image data as a valid 24-bit uncompressed BMP."""
    width = image_data["width"]
    height = image_data["height"]
    pixels = image_data["pixels"]

    row_stride = ((width * 3) + 3) // 4 * 4

    pixel_data_size = row_stride * height

    header_size = 40

    file_size = (
        14
        + header_size
        + pixel_data_size
    )

    img_bytes = bytearray(file_size)

    img_bytes[0:2] = b"BM"

    struct.pack_into(
        "<I",
        img_bytes,
        2,
        file_size,
    )

    struct.pack_into(
        "<H",
        img_bytes,
        6,
        0,
    )

    struct.pack_into(
        "<H",
        img_bytes,
        8,
        0,
    )

    struct.pack_into(
        "<I",
        img_bytes,
        10,
        14 + header_size,
    )

    struct.pack_into(
        "<I",
        img_bytes,
        14,
        header_size,
    )

    struct.pack_into(
        "<i",
        img_bytes,
        18,
        width,
    )

    struct.pack_into(
        "<i",
        img_bytes,
        22,
        height,
    )

    struct.pack_into(
        "<H",
        img_bytes,
        26,
        1,
    )

    struct.pack_into(
        "<H",
        img_bytes,
        28,
        24,
    )

    struct.pack_into(
        "<I",
        img_bytes,
        30,
        0,
    )

    struct.pack_into(
        "<I",
        img_bytes,
        34,
        pixel_data_size,
    )

    struct.pack_into(
        "<i",
        img_bytes,
        38,
        2835,
    )

    struct.pack_into(
        "<i",
        img_bytes,
        42,
        2835,
    )

    struct.pack_into(
        "<I",
        img_bytes,
        46,
        0,
    )

    struct.pack_into(
        "<I",
        img_bytes,
        50,
        0,
    )

    offset = 14 + header_size

    for y in range(height):
        row_base = (
            offset
            + (height - 1 - y) * row_stride
        )

        for x in range(width):
            r, g, b = pixels[
                y * width + x
            ]

            idx = row_base + x * 3

            img_bytes[idx] = b
            img_bytes[idx + 1] = g
            img_bytes[idx + 2] = r

    with open(file_path, "wb") as handle:
        handle.write(img_bytes)


def get_rgb_pixels(image):
    """Return the flat RGB pixel data."""
    return image["pixels"]


def sample_png_lsb(path, sample_count=100000):
    """
    Perform LSB analysis using evenly distributed rows and pixels.

    The function does not create a Python list of all image pixels.
    """

    if sample_count <= 0:
        raise ValueError("sample_count must be greater than zero.")

    png = _parse_png(path)

    width = png["width"]
    height = png["height"]
    color_type = png["color_type"]
    raw = png["raw"]

    channels = 4 if color_type == 6 else 3
    stride = width * channels
    row_size = 1 + stride

    total_pixels = width * height

    # Analyze at most 100 rows.
    rows_to_sample = min(height, 100)

    # Distribute samples across selected rows.
    pixels_per_row = max(
        1,
        min(width, sample_count // rows_to_sample)
    )

    counts = {
        "red": {"zero": 0, "one": 0},
        "green": {"zero": 0, "one": 0},
        "blue": {"zero": 0, "one": 0},
    }

    # Pre-calculate selected rows.
    if rows_to_sample == 1:
        selected_rows = {0}
    else:
        selected_rows = {
            round(i * (height - 1) / (rows_to_sample - 1))
            for i in range(rows_to_sample)
        }

    previous_row = bytearray(stride)
    actual_samples = 0

    for y in range(height):

        raw_position = y * row_size

        filter_type = raw[raw_position]

        filtered_row = raw[
            raw_position + 1:
            raw_position + 1 + stride
        ]

        # ---------------------------------------------------------
        # Reconstruct the row.
        # ---------------------------------------------------------

        row = bytearray(stride)

        if filter_type == 0:

            row[:] = filtered_row

        elif filter_type == 1:

            for i, value in enumerate(filtered_row):

                left = (
                    row[i - channels]
                    if i >= channels
                    else 0
                )

                row[i] = (value + left) & 0xFF

        elif filter_type == 2:

            for i, value in enumerate(filtered_row):

                row[i] = (
                    value + previous_row[i]
                ) & 0xFF

        elif filter_type == 3:

            for i, value in enumerate(filtered_row):

                left = (
                    row[i - channels]
                    if i >= channels
                    else 0
                )

                above = previous_row[i]

                row[i] = (
                    value + ((left + above) // 2)
                ) & 0xFF

        elif filter_type == 4:

            for i, value in enumerate(filtered_row):

                left = (
                    row[i - channels]
                    if i >= channels
                    else 0
                )

                above = previous_row[i]

                upper_left = (
                    previous_row[i - channels]
                    if i >= channels
                    else 0
                )

                row[i] = (
                    value
                    + _paeth_predictor(
                        left,
                        above,
                        upper_left,
                    )
                ) & 0xFF

        else:

            raise UnsupportedImageFormatError(
                f"Unsupported PNG filter type: {filter_type}."
            )

        # ---------------------------------------------------------
        # Analyze only selected rows.
        # ---------------------------------------------------------

        if y in selected_rows:

            if pixels_per_row >= width:

                pixel_positions = range(width)

            else:

                step = width / pixels_per_row

                pixel_positions = (
                    int(i * step)
                    for i in range(pixels_per_row)
                )

            for x in pixel_positions:

                base = x * channels

                red = row[base]
                green = row[base + 1]
                blue = row[base + 2]

                if red & 1:
                    counts["red"]["one"] += 1
                else:
                    counts["red"]["zero"] += 1

                if green & 1:
                    counts["green"]["one"] += 1
                else:
                    counts["green"]["zero"] += 1

                if blue & 1:
                    counts["blue"]["one"] += 1
                else:
                    counts["blue"]["zero"] += 1

                actual_samples += 1

        previous_row = row

    # -------------------------------------------------------------
    # Calculate percentages.
    # -------------------------------------------------------------

    if actual_samples == 0:
        raise ValueError("No pixels were sampled.")

    for channel in counts.values():

        channel["zero_percentage"] = (
            channel["zero"] / actual_samples * 100
        )

        channel["one_percentage"] = (
            channel["one"] / actual_samples * 100
        )

    return {
        "sample_count": actual_samples,
        "total_pixels": total_pixels,
        "rows_analyzed": rows_to_sample,
        "channels": counts,
    }