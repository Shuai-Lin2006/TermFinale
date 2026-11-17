"""Scoped generation: PDF is sliced before pipeline; policy enforced."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from tfv2.product import page_generate


def make_pdf(path: Path, pages: int):
    doc = pymupdf.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 72), f"page {i+1}")
    doc.save(str(path)); doc.close()


class ScopedGenerateTests(unittest.TestCase):
    def test_precise_slices_before_generation(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "book.pdf"; make_pdf(src, 120)
            seen = {}

            def fake(path, **kwargs):
                d = pymupdf.open(str(path)); seen["pages"] = len(d); d.close()
                return {"id": "x"}

            with patch.object(page_generate.generate, "generate_lecture", fake):
                out = page_generate.generate_scoped(src, "1-10", mode="precise", title="t")
            self.assertEqual(seen["pages"], 10)
            self.assertEqual(out["scope"]["page_count"], 10)
            self.assertEqual(out["scope"]["mode"], "precise")

    def test_approx_allowed_over_100(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "book.pdf"; make_pdf(src, 120)
            with patch.object(page_generate.generate, "generate_lecture", lambda *a, **k: {"id": "x"}):
                out = page_generate.generate_scoped(src, "1-110", mode="approx", title="t")
            self.assertEqual(out["scope"]["mode"], "approx")

    def test_under_100_approx_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "book.pdf"; make_pdf(src, 50)
            with self.assertRaises(page_generate.ScopedGenerationError):
                page_generate.generate_scoped(src, "1-20", mode="approx", title="t")


if __name__ == "__main__":
    unittest.main()
