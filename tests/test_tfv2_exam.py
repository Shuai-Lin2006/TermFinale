"""训练模式：100 分蓝图和混合题型解析。"""
from __future__ import annotations

import unittest

from tfv2.product import exam


class ExamTests(unittest.TestCase):
    def test_blueprint_normalizes_to_100(self) -> None:
        secs = exam._norm_sections([
            {"name": "选择题", "type": "choice", "count": 10, "score": 30},
            {"name": "计算题", "type": "calculation", "count": 4, "score": 50},
            {"name": "简答题", "type": "short_answer", "count": 2, "score": 10},
        ])
        self.assertEqual(sum(s["score"] for s in secs), 100)
        self.assertTrue(all(s["score"] >= s["count"] for s in secs))

    def test_too_few_questions_rejected(self) -> None:
        with self.assertRaises(exam.ExamError):
            exam._norm_sections([{"name": "选择题", "type": "choice", "count": 4, "score": 100}])

    def test_choice_and_calculation_parse(self) -> None:
        page_text = {1: "电路换路定则与三要素法。", 2: "RC 电路响应。"}
        choice, issue = exam._parse_question({
            "qtype": "choice", "stem": "换路瞬间电容电压满足什么？", "options": ["突变", "不突变", "为零", "无穷"],
            "answer": 1, "analysis": "由换路定则，电容电压不能突变，因此选 B。", "source_page": 1, "source_no": "1",
        }, {1, 2}, page_text, "mock", "电路")
        self.assertEqual(issue, "")
        self.assertEqual(choice["qtype"], "choice")
        calc, issue = exam._parse_question({
            "qtype": "calculation", "stem": "求 RC 电路的时间常数。", "options": [], "answer_text": "τ=RC",
            "analysis": "一阶 RC 电路的时间常数等于等效电阻乘电容。", "source_page": 2, "source_no": "2",
        }, {1, 2}, page_text, "mock", "电路", expected_type="calculation")
        self.assertEqual(issue, "")
        self.assertEqual(calc["qtype"], "calculation")
        self.assertEqual(calc["answer_audit"], "manual")
        withfig, issue = exam._parse_question({
            "qtype": "calculation", "stem": "根据给出的 RC 电路图，求换路后的时间常数。", "options": [], "answer_text": "τ=RC",
            "analysis": "一阶电路时间常数等于等效电阻乘电容。", "source_page": 1, "source_no": "1",
        }, {1, 2}, page_text, "mock", "电路", expected_type="calculation",
            figure_map={1: {"asset_path": "assets/fig.png", "caption": "资料原图"}})
        self.assertEqual(issue, "")
        # 新题模式绝不从资料页抓图；需要图时走 figure_spec。
        self.assertEqual(withfig["figure_asset"], "")
        self.assertFalse(withfig["original_figure"])
        original, issue = exam._parse_question({
            "qtype": "calculation", "stem": "根据原题图，求换路后的时间常数。", "options": [],
            "answer_text": "τ=RC", "analysis": "一阶电路时间常数等于等效电阻乘电容。",
            "source_page": 1, "source_no": "1", "original_figure": True,
        }, {1, 2}, page_text, "change_numbers", "电路", expected_type="calculation",
            figure_map={1: {"asset_path": "assets/fig.png", "caption": "资料原图"}})
        self.assertEqual(issue, "")
        self.assertEqual(original["figure_asset"], "assets/fig.png")
        self.assertTrue(original["original_figure"])
        # 原题页有图，但题目没有提到图，不能自动塞图。
        no_ref, issue = exam._parse_question({
            "qtype": "calculation", "stem": "某 RC 电路在换路后需要求出时间常数并说明计算依据。", "options": [],
            "answer_text": "τ=RC", "analysis": "一阶电路时间常数等于等效电阻乘电容。",
            "source_page": 1, "source_no": "1", "needs_figure": False,
            "figure_description": "无图",
        }, {1, 2}, page_text, "change_numbers", "电路", expected_type="calculation",
            figure_map={1: {"asset_path": "assets/fig.png", "caption": "资料原图"}})
        self.assertEqual(issue, "")
        self.assertEqual(no_ref["figure_asset"], "")


if __name__ == "__main__":
    unittest.main()
