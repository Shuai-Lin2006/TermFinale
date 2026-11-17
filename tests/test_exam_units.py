"""按资料页出卷：分值、审计、页码不许造。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tfv2.product import exam_units


class FakeClient:
    def __init__(self, questions):
        self.questions = questions
        self.calls = 0

    def json(self, system, user, **kwargs):
        self.calls += 1
        return {"questions": self.questions}


def _q(stem: str, page: int, answer: int = 0, explain: str = "解析") -> dict:
    return {"stem": stem, "options": ["甲", "乙", "丙", "丁"], "answer": answer,
            "explanation": explain, "page": page}


class ExamUnitsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.dir = Path(self._td.name)
        rows = [{"page": i, "text": f"第{i}页 三极管的电流放大系数与输入输出特性曲线内容"} for i in range(1, 7)]
        (self.dir / "source_pages.json").write_text(
            json.dumps({"version": 1, "page_count": len(rows), "pages": rows}, ensure_ascii=False),
            encoding="utf-8")
        self.patch = patch.object(exam_units, "artifact_path", return_value=self.dir)
        self.patch.start()

    def tearDown(self) -> None:
        self.patch.stop()
        self._td.cleanup()

    def _run(self, questions, *, pages=(1, 2, 3), count=3):
        return exam_units.exam_from_units("aid", list(pages), count=count,
                                          subject="模拟电子技术",
                                          client=FakeClient(questions))

    def test_scores_add_up_to_full_marks(self) -> None:
        doc = self._run([_q("放大器输入特性", 1), _q("输出特性曲线", 2), _q("放大倍数计算", 3)])
        self.assertAlmostEqual(doc["content"]["total_score"], 100.0, places=1)
        self.assertEqual(len(doc["questions"]), 3)
        for q in doc["questions"]:
            self.assertGreater(q["score"], 0)
        self.assertEqual(doc["status"], "validated")

    def test_score_drift_stays_at_100(self) -> None:
        doc = self._run([_q(f"第{i}个考点分析", i) for i in (1, 2, 3)], count=3)
        self.assertAlmostEqual(sum(q["score"] for q in doc["questions"]), 100.0, places=1)

    def test_wrong_page_is_dropped_not_remapped(self) -> None:
        doc = self._run([_q("正常题", 1), _q("页码编造的题", 9)], count=2)
        self.assertEqual(len(doc["questions"]), 1)
        self.assertEqual(doc["dropped_questions"][0]["reason"], "页码 9 不在选定页内")
        self.assertEqual(doc["status"], "review")
        pages = {q["page"] for q in doc["questions"]}
        self.assertTrue(pages.issubset({1, 2, 3}))

    def test_duplicate_stem_fails_audit(self) -> None:
        doc = self._run([_q("同一个题目", 1), _q("同一个题目", 2)], count=2)
        self.assertFalse(doc["content"]["answer_audit"]["passed"])
        self.assertEqual(doc["content"]["answer_audit"]["duplicates"], [2])
        self.assertEqual(doc["status"], "review")

    def test_missing_explanation_is_reported(self) -> None:
        doc = self._run([_q("没有解析的题", 1, explain="")], count=1)
        problems = " ".join(doc["content"]["answer_audit"]["problems"])
        self.assertIn("缺少解析", problems)

    def test_duplicate_options_are_dropped(self) -> None:
        bad = {"stem": "选项重复", "options": ["甲", "甲", "乙", "丙"], "answer": 0,
               "explanation": "解析", "page": 1}
        doc = self._run([bad, _q("正常题", 2)], count=2)
        self.assertEqual(len(doc["questions"]), 1)
        self.assertEqual(doc["dropped_questions"][0]["reason"], "题干/选项/答案不合法")

    def test_pages_out_of_artifact_range_rejected(self) -> None:
        with self.assertRaises(ValueError):
            exam_units.exam_from_units("aid", [1, 99], count=1, client=FakeClient([]))

    def test_formula_pages_are_skipped_and_reported(self) -> None:
        rows = [{"page": 1, "text": "正文内容" * 30}]
        (self.dir / "source_pages.json").write_text(
            json.dumps({"version": 1, "page_count": 2,
                        "pages": rows + [{"page": 2, "text": "\ufffd\ue000 公式影像页"}]}, ensure_ascii=False),
            encoding="utf-8")
        doc = exam_units.exam_from_units("aid", [1, 2], count=1, client=FakeClient([_q("题", 1)]))
        self.assertEqual(doc["skipped_pages"], [2])
        self.assertIn("公式/图片页跳过", " ".join(doc["issues"]))

    def test_all_formula_pages_raise(self) -> None:
        (self.dir / "source_pages.json").write_text(
            json.dumps({"version": 1, "page_count": 1,
                        "pages": [{"page": 1, "text": "\ufffd\ue000"}]}, ensure_ascii=False),
            encoding="utf-8")
        with self.assertRaises(ValueError):
            exam_units.exam_from_units("aid", [1], count=1, client=FakeClient([]))


if __name__ == "__main__":
    unittest.main()
