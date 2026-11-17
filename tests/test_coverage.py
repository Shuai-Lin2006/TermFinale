"""G1: page ledger + module coverage (deterministic, no LLM)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pymupdf
from PIL import Image

from tfv2.product import coverage


class CoverageTests(unittest.TestCase):
    def _pdf(self, path: Path) -> None:
        doc = pymupdf.open()
        page = doc.new_page(); page.insert_text((72, 72), "Page one body text, long enough for coverage.")
        doc.new_page()
        page = doc.new_page(); Image.new("RGB", (200, 100), "white").save(path.with_suffix(".png"))
        page.insert_image(pymupdf.Rect(50, 50, 250, 150), filename=str(path.with_suffix(".png")))
        doc.save(str(path)); doc.close()

    def test_scan_pdf_counts_text_blank_image(self):
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "sample.pdf"
            self._pdf(pdf)
            led = coverage.scan_pdf(pdf)
            self.assertEqual(led["page_count"], 3)
            self.assertEqual(led["coverage_percent"], 100.0)
            self.assertEqual(led["status_counts"].get("text"), 1)
            self.assertEqual(led["status_counts"].get("blank"), 1)
            self.assertEqual(led["status_counts"].get("image"), 1)
            self.assertEqual(led["failed_pages"], [])

    def test_module_coverage_reports_missing_pages(self):
        doc = {"kind": "extract_points", "content": {"items": [
            {"point": "A", "page": 1}, {"point": "B", "page": 2}]}}
        out = coverage.module_coverage(doc, 5)
        self.assertEqual(out["coverage_percent"], 40.0)
        self.assertEqual(out["missing_pages"], [3, 4, 5])
        self.assertFalse(out["passed"])

    def test_write_report(self):
        with tempfile.TemporaryDirectory() as td:
            path = coverage.write_report(td, {"page_count": 1, "coverage_percent": 100.0},
                                         [{"kind": "lecture", "passed": True}])
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["page_ledger"]["page_count"], 1)
            self.assertEqual(data["modules"][0]["kind"], "lecture")
            self.assertEqual(data["cost"]["llm_calls"], 0)


if __name__ == "__main__":
    unittest.main()
