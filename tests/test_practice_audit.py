"""Exercise pages must not be counted as missing lecture coverage."""
from __future__ import annotations

import unittest

from tfv2.quality.coverage_audit import is_practice_page


class PracticeAuditTests(unittest.TestCase):
    def test_exercise_page(self):
        text = "思考题和习题\n1. 什么是本征半导体？\n2. 画出波形。\n3. 试求静态工作点。"
        self.assertTrue(is_practice_page(text))

    def test_content_page_is_not_practice(self):
        text = "2.2 放大电路的直流工作状态\n三极管要工作在放大区，发射结正偏，集电结反偏。"
        self.assertFalse(is_practice_page(text))


if __name__ == "__main__":
    unittest.main()
