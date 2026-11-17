"""Long-document splitter: TOC mapping + full page coverage."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pymupdf

from tfv2.product import longdoc


def make_pdf(td: Path, toc: bool, headings: bool = False, pages: int = 300) -> Path:
    path = td / "long.pdf"
    doc = pymupdf.open()
    starts = [2 + 30 * i for i in range(10)]
    for i in range(pages):
        page = doc.new_page()
        if i == 0 and toc:
            for n, start in enumerate(starts, start=1):
                page.insert_text((72, 72 + n * 14), f"{n} Test Chapter {n} ........ {start}")
        elif headings and i + 1 in starts:
            n = starts.index(i + 1) + 1
            page.insert_text((72, 72), f"{n} Test Chapter {n}")
        else:
            page.insert_text((72, 72), f"正文第{i+1}页")
    doc.save(str(path))
    doc.close()
    return path


class LongDocTests(unittest.TestCase):
    def test_toc_300_pages_no_gap(self):
        with tempfile.TemporaryDirectory() as td:
            p = make_pdf(Path(td), toc=True, pages=300)
            out = longdoc.split_pdf(p)
            self.assertEqual(out["page_count"], 300)
            self.assertEqual(out["source"], "toc")
            covered = []
            for c in out["chapters"]:
                covered += list(range(c["start"], c["end"] + 1))
            self.assertEqual(sorted(covered), list(range(1, 301)))
            self.assertGreaterEqual(len(out["chapters"]), 10)

    def test_heading_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            p = make_pdf(Path(td), toc=False, headings=True, pages=60)
            out = longdoc.split_pdf(p)
            self.assertEqual(out["source"], "heading")
            self.assertGreaterEqual(len(out["chapters"]), 2)

    def test_no_toc_returns_one_honest_section(self):
        with tempfile.TemporaryDirectory() as td:
            p = make_pdf(Path(td), toc=False, headings=False, pages=10)
            out = longdoc.split_pdf(p)
            self.assertEqual(out["source"], "fallback")
            self.assertEqual(len(out["chapters"]), 1)
            self.assertEqual(out["chapters"][0]["start"], 1)
            self.assertEqual(out["chapters"][0]["end"], 10)


if __name__ == "__main__":
    unittest.main()
