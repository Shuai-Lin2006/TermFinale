"""答案双解：字母/填空比较；计算题标人工。"""
from __future__ import annotations

import unittest

from core.quality.answer_verify import answer_key, compare

MD = """# 答案与解析

## 单项选择题

1. **B**。解析。
2. **A**。解析。

## 填空题

1. **-1；x+y=3**。解析。
"""
GOT = {("单项选择题", 1): "B", ("单项选择题", 2): "C", ("填空题", 1): "-1; x+y=3"}


class AnswerVerifyTest(unittest.TestCase):
    def test_compare(self):
        key = answer_key(MD.split("# 答案与解析", 1)[1])
        r = compare(key, GOT)
        self.assertEqual(r.total, 3)
        self.assertEqual(r.match, 2)
        self.assertEqual(r.mismatch, 1)

    def test_equivalent_equation(self):
        from core.quality.answer_verify import compare
        key = {("填空题", 1): "-1；x+y=3"}
        got = {("填空题", 1): "-1; y=-x+3"}
        r = compare(key, got)
        self.assertEqual(r.match, 1, r.items)
