"""Universal ingress: docx and pptx both produce PageLedger."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from tfv2.ingest.universal import open_source


class Tests(unittest.TestCase):
    def test_docx(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.docx"; d = Document(); d.add_paragraph("放大电路静态工作点"); d.save(p)
            l = open_source(p); self.assertGreaterEqual(l.page_count, 1); self.assertTrue(l.pages[0].text)

    def test_pptx(self):
        from pptx import Presentation
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.pptx"; pr = Presentation(); s = pr.slides.add_slide(pr.slide_layouts[5]); s.shapes.title.text = "放大电路"; pr.save(p)
            l = open_source(p); self.assertGreaterEqual(l.page_count, 1); self.assertIn("放大电路", l.pages[0].text)


if __name__ == "__main__":
    unittest.main()
