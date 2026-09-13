import os
import tempfile
import unittest

from core.embed import embed_message
from core.extract import extract_message
from core.image import read_image


class TestEmbed(unittest.TestCase):
    def test_embed_and_extract_roundtrip_png(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = os.path.join(temp_dir, "source.png")
            output = os.path.join(temp_dir, "stego.png")

            # Create a simple 10x10 PNG image
            width = 10
            height = 10
            pixels = []
            for _ in range(width * height):
                pixels.append((10, 20, 30))

            from core.image import write_image
            write_image(source, {"format": "PNG", "width": width, "height": height, "pixels": pixels, "color_type": 2})
            embed_message("hello", source, output)
            result = extract_message(output)
            self.assertEqual(result["message"], "hello")


    def test_read_png_standard_filters(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            import struct
            import zlib

            path = os.path.join(temp_dir, "filtered.png")
            width, height = 3, 2
            rows = [
                bytes([10, 20, 30, 40, 50, 60, 70, 80, 90]),
                bytes([15, 25, 35, 45, 55, 65, 75, 85, 95]),
            ]

            def paeth(left, above, upper_left):
                p = left + above - upper_left
                pa, pb, pc = abs(p-left), abs(p-above), abs(p-upper_left)
                return left if pa <= pb and pa <= pc else (above if pb <= pc else upper_left)

            filtered = bytearray()
            previous = bytes(width * 3)
            for filter_type, row in enumerate(rows):
                filtered.append(filter_type)
                for i, value in enumerate(row):
                    left = row[i-3] if i >= 3 else 0
                    above = previous[i]
                    upper_left = previous[i-3] if i >= 3 else 0
                    if filter_type == 0:
                        f = value
                    elif filter_type == 1:
                        f = (value - left) & 0xFF
                    elif filter_type == 2:
                        f = (value - above) & 0xFF
                    elif filter_type == 3:
                        f = (value - ((left + above) // 2)) & 0xFF
                    else:
                        f = (value - paeth(left, above, upper_left)) & 0xFF
                    filtered.append(f)
                previous = row

            def chunk(kind, data):
                return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

            ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
            png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(filtered))) + chunk(b"IEND", b"")
            with open(path, "wb") as handle:
                handle.write(png)

            image = read_image(path)
            self.assertEqual(image["pixels"], [(10,20,30), (40,50,60), (70,80,90), (15,25,35), (45,55,65), (75,85,95)])

    def test_embed_and_extract_roundtrip_bmp(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = os.path.join(temp_dir, "source.bmp")
            output = os.path.join(temp_dir, "stego.bmp")

            width = 10
            height = 10
            pixels = []
            for _ in range(width * height):
                pixels.append((10, 20, 30))

            from core.image import write_image
            write_image(source, {"format": "BMP", "width": width, "height": height, "pixels": pixels})
            embed_message("test", source, output)
            result = extract_message(output)
            self.assertEqual(result["message"], "test")


if __name__ == "__main__":
    unittest.main()
