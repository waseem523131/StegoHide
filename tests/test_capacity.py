import unittest

from core.capacity import calculate_capacity, check_capacity


class TestCapacity(unittest.TestCase):
    def test_calculate_capacity(self):
        result = calculate_capacity(10, 10)
        self.assertEqual(result["pixels"], 100)
        self.assertEqual(result["capacity_bits"], 300)
        self.assertEqual(result["capacity_bytes"], 37)

    def test_check_capacity(self):
        result = check_capacity(2, 10, 10)
        self.assertTrue(result["sufficient"])


if __name__ == "__main__":
    unittest.main()
