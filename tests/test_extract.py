import os
import tempfile
import unittest

from core.extract import extract_message
from utils.errors import NoStegoMessageFoundError


class TestExtract(unittest.TestCase):
    def test_no_stego_message_found(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = os.path.join(temp_dir, "plain.png")
            from core.image import write_image
            write_image(image_path, {"format": "PNG", "width": 10, "height": 10, "pixels": [(1, 2, 3)] * 100, "color_type": 2})
            with self.assertRaises(NoStegoMessageFoundError):
                extract_message(image_path)


if __name__ == "__main__":
    unittest.main()
