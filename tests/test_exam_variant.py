
"""Round 9: reference question bank + variant_of normalization."""
from __future__ import annotations

import unittest

from tfv2.product import exam


class ReferenceBankTests(unittest.TestCase):
    def test_fallback_parses_numbered_questions(self):
        text = "一、选择题\n1. 神经传导\n2. 突触传递\n二、简答题\n3. 反射弧"
        items = exam._reference_bank_fallback(text)
        self.assertEqual([x["no"] for x in items], ["1", "2", "3"])
        self.assertEqual(items[0]["type"], "choice")
        self.assertEqual(items[-1]["type"], "short_answer")

    def test_bank_uses_fallback_when_model_empty(self):
        class Fake:
            def json(self, *a, **k):
                return {"items": []}
        bank = exam._reference_bank(
            Fake(), "一、选择题\n1. 神经传导\nA. 甲 B. 乙 C. 丙 D. 丁\n答案：A\n2. 突触传递\nA. 甲 B. 乙 C. 丙 D. 丁\n答案：B")
        self.assertEqual(len(bank["items"]), 2)
        self.assertTrue(bank["used"])

    def test_variant_of_is_normalized(self):
        raw = {
            "qtype": "choice", "stem": "患者出现神经传导异常的临床情境分析",
            "options": ["A", "B", "C", "D"], "answer": 0,
            "analysis": "神经传导内容解释，说明动作电位如何传播。", "source_page": 1, "source_no": "1",
            "variant_of": "第3/15题",
        }
        q, issue = exam._parse_question(raw, {1}, {1: "神经传导"}, "variant", "医学", expected_type="choice")
        self.assertEqual(issue, "")
        self.assertEqual(q["variant_of"], "3")


if __name__ == "__main__":
    unittest.main()
