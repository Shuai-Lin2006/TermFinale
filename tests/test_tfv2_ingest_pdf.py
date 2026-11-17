"""PDF 页账本测试。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pymupdf

from tfv2.ingest.pdf import build_pdf_page_ledger


class PdfIngestTests(unittest.TestCase):
    def test_build_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.pdf"
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 72), "This is a test page with enough text for extraction.")
            doc.save(p); doc.close()
            led = build_pdf_page_ledger(p, material_name="x.pdf")
            self.assertEqual(led.page_count, 1)
            self.assertIn("test page", led.pages[0].text)
            self.assertEqual(led.pages[0].quality.value, "text")


if __name__ == "__main__":
    unittest.main()
