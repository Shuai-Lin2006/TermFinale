"""试卷生成清洗：单题型不能带答案/别的题型；答案只保留第一段。"""
from __future__ import annotations

import unittest

from core.exam_engine import _clean_answer_output, _clean_section_output


class SectionCleanTest(unittest.TestCase):
    def test_keeps_only_requested_section(self):
        md = """## 单项选择题（4 题，每题 5 分，共 20 分）

1. 题干一
A. 1 B. 2

2. 题干二

# 答案与解析

1. A
2. B

## 填空题（2 题，每题 10 分，共 20 分）

1. 另一套题
"""
        out = _clean_section_output(md, "单项选择题", 4, 5)
        self.assertIn("## 单项选择题（4 题，每题 5 分，共 20 分）", out)
        self.assertIn("题干一", out)
        self.assertIn("题干二", out)
        self.assertNotIn("答案与解析", out)
        self.assertNotIn("填空题", out)
        self.assertNotIn("另一套题", out)

    def test_no_requested_heading_is_dropped_when_mixed(self):
        md = "## 填空题（2 题，每题 10 分，共 20 分）\n\n1. 别的题"
        self.assertEqual(_clean_section_output(md, "单项选择题", 4, 5), "")

    def test_plain_questions_are_wrapped(self):
        md = "1. 第一题\n2. 第二题"
        out = _clean_section_output(md, "单项选择题", 2, 10)
        self.assertTrue(out.startswith("## 单项选择题（2 题，每题 10 分，共 20 分）"))
        self.assertIn("第一题", out)


class AnswerCleanTest(unittest.TestCase):
    def test_keeps_first_answer_section_only(self):
        md = """# 答案与解析

## 单项选择题
1. A
2. B

## 填空题
1. 42

# 答案与解析

1. 又来一套
"""
        out = _clean_answer_output(md)
        self.assertIn("1. A", out)
        self.assertIn("1. 42", out)
        self.assertNotIn("又来一套", out)
        self.assertEqual(out.count("# 答案与解析"), 1)

    def test_cuts_second_paper_heading(self):
        md = """# 答案与解析
1. A
2. B

## 单项选择题（4 题，每题 5 分，共 20 分）
1. 新题
"""
        out = _clean_answer_output(md)
        self.assertIn("1. A", out)
        self.assertNotIn("新题", out)
        self.assertNotIn("单项选择题（4 题", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
