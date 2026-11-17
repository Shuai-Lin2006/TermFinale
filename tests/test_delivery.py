
"""Round 2: delivery policy — hard rejects, soft delivers, partial exportable."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.product import delivery, service


def exam_doc(*, pages, cited, total=100, conflicts=0, checked=True, questions=2):
    qs = [{
        "qtype": "choice", "stem": f"第{i+1}题：关于{["交感神经节前纤维","牵涉性痛","交感干神经节","灰交通支"][i % 4]}的临床情境，选择正确项。",
        "options": ["A", "B", "C", "D"], "answer": 0, "answer_text": "A",
        "analysis": "A 项正确，B/C/D 不符合。", "source_page": cited[i % len(cited)],
        "score": total / questions,
    } for i in range(questions)]
    return {
        "kind": "exam", "status": "validated", "issues": [],
        "coverage": {"pages": pages, "pages_cited": sorted(set(cited))},
        "content": {
            "sections": [{"name": "一、选择题", "type": "choice", "count": questions,
                          "score": total, "questions": qs}],
            "total_score": total,
            "answer_audit": {"checked": checked, "conflicts": [
                {"no": i + 1, "paper": 0, "audit": 1} for i in range(conflicts)
            ]},
        },
    }


class ExamDeliveryTests(unittest.TestCase):
    def test_validated(self):
        out = delivery.apply_exam_delivery(exam_doc(pages=[1, 2, 3, 4], cited=[1, 2, 3, 4]))
        self.assertEqual(out["status"], "validated")
        self.assertTrue(out["delivery"]["exportable"])

    def test_low_coverage_is_partial_not_rejected(self):
        out = delivery.apply_exam_delivery(exam_doc(pages=list(range(1, 8)), cited=[1, 2]))
        self.assertEqual(out["status"], "partial")
        self.assertIn(5, out["delivery"]["missing_pages"])

    def test_one_conflict_is_review(self):
        out = delivery.apply_exam_delivery(exam_doc(pages=[1, 2, 3, 4], cited=[1, 2, 3, 4], conflicts=1))
        self.assertEqual(out["status"], "review")

    def test_two_conflicts_are_hard(self):
        out = delivery.apply_exam_delivery(exam_doc(pages=[1, 2, 3, 4], cited=[1, 2, 3, 4], conflicts=2))
        self.assertEqual(out["status"], "rejected")

    def test_bad_total_is_hard(self):
        out = delivery.apply_exam_delivery(exam_doc(pages=[1, 2, 3, 4], cited=[1, 2, 3, 4], total=90))
        self.assertEqual(out["status"], "rejected")

    def test_unchecked_audit_is_review(self):
        out = delivery.apply_exam_delivery(exam_doc(pages=[1, 2, 3, 4], cited=[1, 2, 3, 4], checked=False))
        self.assertEqual(out["status"], "review")

    def test_no_questions_rejected(self):
        doc = exam_doc(pages=[1], cited=[1], questions=0)
        out = delivery.apply_exam_delivery(doc)
        self.assertEqual(out["status"], "rejected")
        self.assertFalse(out["delivery"]["exportable"])


class TaskDeliveryTests(unittest.TestCase):
    def test_partial_items_are_delivered(self):
        doc = {"kind": "extract_points", "status": "validated", "issues": [],
               "coverage": {"pages": [1, 2, 3], "pages_cited": [1], "coverage": 0.33},
               "content": {"items": [{"point": "a", "detail": "b", "page": 1}]}}
        out = delivery.apply_task_delivery(doc)
        self.assertEqual(out["status"], "partial")
        self.assertTrue(out["delivery"]["exportable"])
        self.assertIn(2, out["delivery"]["missing_pages"])

    def test_empty_items_rejected(self):
        doc = {"kind": "extract_points", "status": "validated", "issues": [],
               "coverage": {"pages": [1], "pages_cited": [], "coverage": 0.0},
               "content": {"items": []}}
        out = delivery.apply_task_delivery(doc)
        self.assertEqual(out["status"], "rejected")

    def test_complete_items_validated(self):
        doc = {"kind": "extract_points", "status": "validated", "issues": [],
               "coverage": {"pages": [1], "pages_cited": [1], "coverage": 1.0},
               "content": {"items": [{"point": "a", "detail": "b", "page": 1}]}}
        out = delivery.apply_task_delivery(doc)
        self.assertEqual(out["status"], "validated")


class LecturePartialTests(unittest.TestCase):
    def test_draft_with_pdf_is_partial(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "lecture.html").write_text("<html></html>", encoding="utf-8")
            (p / "lecture.pdf").write_bytes(b"%PDF-1.4\n")
            (p / "sections.json").write_text(json.dumps([{"id": "s1", "title": "s"}]), encoding="utf-8")
            (p / "manifest.json").write_text(json.dumps({
                "draft": True, "gate": {"passed": False},
                "content_gate": {"issues": []}, "pdf_content_gate": {"issues": []},
                "language": {"issues": []},
            }), encoding="utf-8")
            q = service._quality("x", p, json.loads((p / "manifest.json").read_text()))
            self.assertEqual(q["status"], "partial")
            self.assertEqual(q["status_label"], "部分交付")


if __name__ == "__main__":
    unittest.main()
