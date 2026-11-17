"""Book report: chapter status must be auditable, cost must not be invented."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.product import book_report


class BookReportTests(unittest.TestCase):
    def test_summary_and_gate_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            idx = {"source": "x.pdf", "page_count": 20, "split_source": "manual", "chapters": [
                {"id": "ch01", "title": "A", "pages": [1, 10], "page_count": 10,
                 "status": "validated", "artifact_id": "a1", "seconds": 120},
                {"id": "ch02", "title": "B", "pages": [11, 20], "page_count": 10,
                 "status": "done", "artifact_id": "a2", "seconds": 80},
            ]}
            (root / "index.json").write_text(json.dumps(idx), encoding="utf-8")
            (root / "ch01").mkdir()
            (root / "ch01" / "worker_result.json").write_text(
                json.dumps({"artifact_id": "a1", "gate_passed": True,
                            "quality": {"content_passed": True, "pdf_passed": True}}), encoding="utf-8")
            r = book_report.build(root / "index.json")
            self.assertEqual(r["summary"]["chapters"], 2)
            self.assertEqual(r["summary"]["validated"], 1)
            self.assertEqual(r["summary"]["done"], 1)
            self.assertFalse(r["summary"]["all_validated"])
            self.assertIsNone(r["summary"]["cost_cny"])
            self.assertTrue(r["chapters"][0]["gate_passed"])
            self.assertFalse(r["chapters"][1]["gate_passed"])


if __name__ == "__main__":
    unittest.main()
