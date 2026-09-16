"""DOCX steganography utilities for StegoHide."""

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import os
from core.header import create_header, parse_header


# Invisible Unicode characters
ZERO_WIDTH_ZERO = "\u200b"   # Bit 0
ZERO_WIDTH_ONE = "\u200c"    # Bit 1
import tempfile

# Marks the beginning of StegoHide hidden data
STEGO_MARKER = "\u2060"


def bytes_to_hidden_text(data):
    """Convert bytes into invisible Unicode characters."""

    hidden_chars = [STEGO_MARKER]

    for byte in data:
        for bit_position in range(7, -1, -1):
            bit = (byte >> bit_position) & 1

            if bit == 0:
                hidden_chars.append(ZERO_WIDTH_ZERO)
            else:
                hidden_chars.append(ZERO_WIDTH_ONE)

    return "".join(hidden_chars)


def hidden_text_to_bytes(hidden_text):
    """Convert invisible Unicode characters back into bytes."""

    if not hidden_text.startswith(STEGO_MARKER):
        raise ValueError("StegoHide marker not found.")

    bit_chars = hidden_text[len(STEGO_MARKER):]

    bits = []

    for char in bit_chars:

        if char == ZERO_WIDTH_ZERO:
            bits.append(0)

        elif char == ZERO_WIDTH_ONE:
            bits.append(1)

    if not bits:
        raise ValueError("No hidden data found.")

    if len(bits) % 8 != 0:
        raise ValueError("Corrupted hidden data.")

    result = bytearray()

    for index in range(0, len(bits), 8):

        byte_value = 0

        for bit in bits[index:index + 8]:
            byte_value = (byte_value << 1) | bit

        result.append(byte_value)

    return bytes(result)


def _read_document_xml(docx_path):
    """Read word/document.xml from a DOCX file."""

    with ZipFile(docx_path, "r") as archive:

        try:
            return archive.read("word/document.xml")

        except KeyError as exc:
            raise ValueError(
                "Invalid DOCX: word/document.xml not found."
            ) from exc


def _write_docx_with_document_xml(
    source_path,
    output_path,
    document_xml,
):
    """Create a new DOCX while replacing document.xml."""

    source_path = Path(source_path)
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_fd, temp_name = tempfile.mkstemp(
        suffix=".docx",
        dir=output_path.parent,
    )

    os.close(temp_fd)

    try:

        with ZipFile(source_path, "r") as source_archive:

            with ZipFile(
                temp_name,
                "w",
                ZIP_DEFLATED,
            ) as output_archive:

                for item in source_archive.infolist():

                    if item.filename == "word/document.xml":

                        output_archive.writestr(
                            item,
                            document_xml,
                        )

                    else:

                        output_archive.writestr(
                            item,
                            source_archive.read(
                                item.filename
                            ),
                        )

        os.replace(
            temp_name,
            output_path,
        )

    except Exception:

        if os.path.exists(temp_name):
            os.remove(temp_name)

        raise


def _insert_hidden_data(document_xml, hidden_text):
    """
    Insert hidden StegoHide data into document.xml.

    The data is inserted before w:sectPr because
    w:sectPr should remain the final element in w:body.
    """

    xml_text = document_xml.decode("utf-8")

    # Prevent accidental duplicate insertion
    if STEGO_MARKER in xml_text:
        raise ValueError(
            "This DOCX already contains StegoHide data."
        )

    hidden_paragraph = (
        '<w:p>'
        '<w:r>'
        '<w:t>'
        + hidden_text
        + '</w:t>'
        '</w:r>'
        '</w:p>'
    )

    # Insert before sectPr if it exists
    sectpr_position = xml_text.find("<w:sectPr")

    if sectpr_position != -1:

        modified_xml = (
            xml_text[:sectpr_position]
            + hidden_paragraph
            + xml_text[sectpr_position:]
        )

    else:

        # Fallback: insert before </w:body>
        body_end = xml_text.rfind("</w:body>")

        if body_end == -1:
            raise ValueError(
                "Invalid DOCX: document body not found."
            )

        modified_xml = (
            xml_text[:body_end]
            + hidden_paragraph
            + xml_text[body_end:]
        )

    return modified_xml.encode("utf-8")


def hide_message_in_docx(
    message,
    input_path,
    output_path,
):
    """Hide a UTF-8 text message inside a DOCX document."""

    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"File not found: {input_path}"
        )

    if input_path.suffix.lower() != ".docx":
        raise ValueError(
            "Only DOCX documents are supported."
        )

    if output_path.resolve() == input_path.resolve():
        raise ValueError(
            "Output DOCX must be different from input DOCX."
        )

    # Convert message to UTF-8 bytes
    message_bytes = message.encode("utf-8")

    # Create StegoHide header + message
    payload = create_header(message_bytes)

    # Convert payload to invisible characters
    hidden_text = bytes_to_hidden_text(payload)

    # Read original document.xml
    document_xml = _read_document_xml(
        input_path
    )

    # Insert hidden data
    modified_xml = _insert_hidden_data(
        document_xml,
        hidden_text,
    )

    # Create output DOCX
    _write_docx_with_document_xml(
        input_path,
        output_path,
        modified_xml,
    )

    return {
        "output_path": str(output_path),
        "message_length": len(message_bytes),
    }


def extract_message_from_docx(docx_path):
    """Extract a StegoHide message from a DOCX document."""

    docx_path = Path(docx_path)

    if not docx_path.is_file():
        raise FileNotFoundError(
            f"File not found: {docx_path}"
        )

    if docx_path.suffix.lower() != ".docx":
        raise ValueError(
            "Only DOCX documents are supported."
        )

    # Read document.xml
    document_xml = _read_document_xml(
        docx_path
    )

    xml_text = document_xml.decode("utf-8")

    # Find StegoHide marker
    marker_position = xml_text.find(
        STEGO_MARKER
    )

    if marker_position == -1:
        raise ValueError(
            "No StegoHide message found."
        )

    # Extract from marker until the end of the text element
    text_start = marker_position

    text_end = xml_text.find(
        "</w:t>",
        text_start,
    )

    if text_end == -1:
        raise ValueError(
            "Invalid hidden data."
        )

    hidden_text = xml_text[
        text_start:text_end
    ]

    # Convert invisible characters back to bytes
    payload = hidden_text_to_bytes(
        hidden_text
    )

    # Parse StegoHide header
    header = parse_header(payload)

    message_start = header["header_size"]

    message_length = header["message_length"]

    message_end = (
        message_start
        + message_length
    )

    if len(payload) < message_end:
        raise ValueError(
            "Invalid message length or corrupted data."
        )

    message_bytes = payload[
        message_start:message_end
    ]

    # Decode UTF-8
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
        "message_length": message_length,
    }