import unittest

from tfv2.curriculum.teaching_plan import validate_plan


class TeachingPlanTests(unittest.TestCase):
    def test_valid_plan(self):
        plan = validate_plan([
            {"title": "极限与连续", "pages": [1, 2, 3]},
            {"title": "导数与微分", "pages": [4, 5]},
        ], 5)
        self.assertEqual([x[0] for x in plan or []], ["极限与连续", "导数与微分"])

    def test_missing_page_rejected(self):
        self.assertIsNone(validate_plan([
            {"title": "极限", "pages": [1, 2]},
            {"title": "导数", "pages": [4, 5]},
        ], 5))

    def test_duplicate_or_out_of_order_rejected(self):
        self.assertIsNone(validate_plan([
            {"title": "极限", "pages": [1, 2, 3]},
            {"title": "导数", "pages": [3, 4]},
        ], 4))
        self.assertIsNone(validate_plan([
            {"title": "导数", "pages": [3, 4]},
            {"title": "极限", "pages": [1, 2]},
        ], 4))

    def test_generic_or_duplicate_title_rejected(self):
        self.assertIsNone(validate_plan([
            {"title": "正文", "pages": [1, 2]},
            {"title": "导数", "pages": [3, 4]},
        ], 4))
        self.assertIsNone(validate_plan([
            {"title": "极限", "pages": [1, 2]},
            {"title": "极限", "pages": [3, 4]},
        ], 4))


if __name__ == "__main__":
    unittest.main()
