
"""Deterministic trust checks: these are the regressions that made the old
quality report claim 100% while quoting unrelated pages."""
from __future__ import annotations

import unittest

from tfv2.quality import trust


def block(text: str, pages: list[int], quote: str = "") -> dict:
    return {
        "id": "b1", "kind": "paragraph", "text": text,
        "source_refs": [{"page_start": p, "page_end": p, "quote": quote} for p in pages],
    }


class EvidenceTests(unittest.TestCase):
    def test_relevant_quote_is_verified(self) -> None:
        sections = [{"title": "s", "blocks": [block("叶绿体DNA决定细胞质遗传。", [1], "叶绿体DNA决定细胞质遗传。")]}]
        result = trust.audit_evidence(sections, {1: "叶绿体DNA决定细胞质遗传。"})
        self.assertTrue(result["passed"])
        self.assertEqual(result["verified"], 1)

    def test_unrelated_homework_quote_is_weak(self) -> None:
        sections = [{"title": "s", "blocks": [block("高阶导数需要逐次求导。", [1], "作业 2.2 (A): 9(3)(4)")]}]
        result = trust.audit_evidence(sections, {1: "作业 2.2 (A): 9(3)(4)"})
        self.assertFalse(result["passed"])
        self.assertEqual(result["weak_quote"], 1)

    def test_quote_not_on_page_is_mismatch(self) -> None:
        sections = [{"title": "s", "blocks": [block("叶绿体DNA决定细胞质遗传。", [1], "恭喜发财 纯洁的爱")]}]
        result = trust.audit_evidence(sections, {1: "叶绿体DNA决定细胞质遗传。"})
        self.assertFalse(result["passed"])
        self.assertEqual(result["mismatch"], 1)

    def test_page_only_is_not_verified(self) -> None:
        sections = [{"title": "s", "blocks": [block("完全无关的概括。", [1])]}]
        result = trust.audit_evidence(sections, {1: "叶绿体DNA决定细胞质遗传。"})
        self.assertFalse(result["passed"])
        self.assertEqual(result["page_only"], 1)


class CoverageTests(unittest.TestCase):
    def test_partial_coverage_fails(self) -> None:
        sections = [{"title": "s", "blocks": [block("第一页内容。", [1])]}]
        result = trust.audit_coverage(sections, 4, {i: f"第{i}页内容。" for i in range(1, 5)})
        self.assertFalse(result["passed"])
        self.assertLess(result["page_ratio"], 0.98)

    def test_analysis_with_partial_coverage_is_rejected(self) -> None:
        doc = {
            "kind": "analysis", "status": "validated", "issues": [],
            "coverage": {"pages": list(range(1, 25)), "pages_cited": list(range(1, 17)), "coverage": 0.625},
            "content": {"one_line": "主线", "concepts": ["a", "b", "c"]},
        }
        out = trust.apply_task_trust(doc)
        self.assertEqual(out["status"], "rejected")
        self.assertFalse(out["trust"]["passed"])


class ExamTests(unittest.TestCase):
    def _doc(self, questions: list[dict]) -> dict:
        return {
            "kind": "exam", "status": "validated", "issues": [],
            "coverage": {"pages": list(range(1, 36)), "pages_cited": [1, 2, 3]},
            "content": {
                "sections": [{"name": "一、选择题", "type": "choice", "count": len(questions),
                               "score": 100, "questions": questions}],
                "total_score": 100,
                "answer_audit": {"checked": True, "conflicts": []},
            },
        }

    def test_duplicate_and_self_correction_reject(self) -> None:
        q1 = {"qtype": "choice", "stem": "设 x=t^2+1，求二阶导。", "options": ["1", "2", "3", "4"],
              "answer": 0, "analysis": "重新计算结果为 1。", "source_page": 1, "score": 100}
        q2 = dict(q1)
        doc = self._doc([q1, q2])
        out = trust.apply_exam_trust(doc)
        self.assertEqual(out["status"], "rejected")
        self.assertFalse(out["trust"]["passed"])
        self.assertGreater(out["trust"]["duplicate_questions"], 0)
        self.assertTrue(out["trust"]["self_correction"])

    def test_low_page_coverage_rejects(self) -> None:
        q = {"qtype": "choice", "stem": "求导。", "options": ["1", "2", "3", "4"],
             "answer": 0, "analysis": "结果为 1。", "source_page": 1, "score": 100}
        doc = self._doc([q])
        out = trust.apply_exam_trust(doc)
        self.assertEqual(out["status"], "rejected")
        self.assertLess(out["trust"]["page_ratio"], 0.5)


if __name__ == "__main__":
    unittest.main()
