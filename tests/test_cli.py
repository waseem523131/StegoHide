import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from cli.commands import main
from core.image import write_image


class TestCLI(unittest.TestCase):
    def test_help(self):
        output = StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("StegoHide", output.getvalue())

    def test_hide_and_extract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.png"
            output = Path(temp_dir) / "stego.png"
            pixels = [(10, 20, 30)] * 100
            write_image(source, {"format": "PNG", "width": 10, "height": 10, "pixels": pixels, "color_type": 2})

            hide_output = StringIO()
            with redirect_stdout(hide_output):
                self.assertEqual(
                    main(["hide", "--input", str(source), "--output", str(output), "--message", "hello"]),
                    0,
                )

            extract_output = StringIO()
            with redirect_stdout(extract_output):
                self.assertEqual(main(["extract", "--input", str(output)]), 0)

            self.assertIn("hello", extract_output.getvalue())
            self.assertIn("Report:", hide_output.getvalue())

    def test_capacity_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.png"
            write_image(source, {"format": "PNG", "width": 10, "height": 10, "pixels": [(10, 20, 30)] * 100, "color_type": 2})
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["capacity", str(source)]), 0)
            self.assertIn("Capacity: 300 bits (37 bytes)", output.getvalue())


if __name__ == "__main__":
    unittest.main()
