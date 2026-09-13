import unittest

from core.header import create_header, parse_header, MAGIC_SIGNATURE


class TestHeader(unittest.TestCase):
    def test_create_header(self):
        message = b"Hello"
        result = create_header(message)
        self.assertTrue(result.startswith(MAGIC_SIGNATURE))
        self.assertEqual(len(result), 13 + len(message))

    def test_parse_header(self):
        message = b"Hi"
        data = create_header(message)
        parsed = parse_header(data)
        self.assertEqual(parsed["message_length"], len(message))


if __name__ == "__main__":
    unittest.main()
