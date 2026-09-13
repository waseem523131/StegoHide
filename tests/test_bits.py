import unittest

from core.bits import text_to_bits, bits_to_text


class TestBits(unittest.TestCase):
    def test_text_to_bits(self):
        result = text_to_bits("A")
        self.assertEqual(result, [0,1,0,0,0,0,0,1])

    def test_bits_to_text(self):
        bits = [0,1,0,0,0,0,0,1]
        result = bits_to_text(bits)
        self.assertEqual(result, "A")

    def test_round_trip(self):
        message = "StegoHide"
        bits = text_to_bits(message)
        text = bits_to_text(bits)
        self.assertEqual(text, message)


if __name__ == "__main__":
    unittest.main()
