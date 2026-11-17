
"""Round 7: page-anchored coverage supplement."""
from __future__ import annotations

import unittest

from tfv2.product import exam


class FakeClient:
    def json(self, system, user, **kwargs):
        p = int(user.split("资料页码：")[1].split("\n")[0])
        return {"question": {
            "qtype": "choice", "stem": f"第{p}页神经传导的临床情境分析",
            "options": ["A", "B", "C", "D"], "answer": 0, "answer_text": "A",
            "analysis": f"第{p}页神经传导内容", "source_page": p, "source_no": "x",
            "needs_figure": False, "original_figure": False, "figure_description": "无图",
        }}


class CoverageRepairTests(unittest.TestCase):
    def test_uncovered_pages_get_appended(self):
        bp = {"sections": [{
            "name": "一、选择题", "type": "choice", "count": 2, "score": 100,
            "questions": [
                {"qtype": "choice", "stem": "神经传导基础", "options": ["A", "B", "C", "D"],
                 "answer": 0, "answer_text": "A", "analysis": "基础", "source_page": 1, "score": 50},
                {"qtype": "choice", "stem": "反射弧组成", "options": ["A", "B", "C", "D"],
                 "answer": 0, "answer_text": "A", "analysis": "反射", "source_page": 2, "score": 50},
            ],
        }]}
        page_text = {i: f"第{i}页 神经传导 反射 突触 递质 内容" for i in range(1, 6)}
        exam._repair_exam_coverage(
            bp, list(range(1, 6)), page_text, "mock", "医学", {}, FakeClient()
        )
        sec = bp["sections"][0]
        self.assertGreater(len(sec["questions"]), 2)
        self.assertEqual(sec["count"], len(sec["questions"]))
        self.assertAlmostEqual(sum(q["score"] for q in sec["questions"]), 100.0, places=1)
        self.assertGreaterEqual(len({q["source_page"] for q in sec["questions"]}), 3)


if __name__ == "__main__":
    unittest.main()
