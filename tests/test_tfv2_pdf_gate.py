import unittest
from pathlib import Path
from types import SimpleNamespace
from tfv2.quality.pdf_gate import validate_pdf


class PdfGateTests(unittest.TestCase):
    def test_deliverable_pdf_passes(self):
        p = Path("deliverables/01_电路讲义.pdf")
        if p.is_file():
            self.assertEqual(validate_pdf(p), [])

    def test_generic_toc_is_rejected(self):
        p = Path("deliverables/01_电路讲义.pdf")
        if not p.is_file():
            self.skipTest("no deliverable")
        issues = validate_pdf(p, [SimpleNamespace(title="第一节 正文（第 1–8 页）")])
        self.assertTrue(any("占位标题" in x for x in issues))


if __name__ == "__main__":
    unittest.main()
