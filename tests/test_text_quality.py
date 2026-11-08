"""乱码页识别。"""
from __future__ import annotations

import unittest

from core.quality.text_quality import is_low_quality_page


class TextQualityTest(unittest.TestCase):
    def test_garbled_formula_text(self):
        self.assertTrue(is_low_quality_page("例12 的导数 求函数 x x x y x x x x x x y 解 x x x x x"))

    def test_normal_chinese(self):
        self.assertFalse(is_low_quality_page("隐函数求导：方程两边对 x 求导，再解出 y'。这是本章重点。"))

    def test_empty(self):
        self.assertTrue(is_low_quality_page(""))
