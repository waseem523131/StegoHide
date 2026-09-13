import unittest

from reports.report_manager import create_report, delete_report, open_report


class TestReports(unittest.TestCase):
    def test_create_open_delete_report(self):
        path = create_report("Test", "Success", {"Message Length": 5})
        name = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        try:
            content = open_report(name)
            self.assertIn("StegoHide Report", content)
            self.assertIn("Message Length: 5", content)
        finally:
            delete_report(name)


if __name__ == "__main__":
    unittest.main()
