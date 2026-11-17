
"""Source page cache: tasks must read the original page, not the lecture."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pymupdf

from tfv2.product import source_pages


class SourcePageCacheTests(unittest.TestCase):
    def test_pdf_cache_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = Path(td) / "art"
            (art / "source").mkdir(parents=True)
            pdf = art / "source" / "unit.pdf"
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Chloroplast DNA determines cytoplasmic inheritance")
            page = doc.new_page()
            page.insert_text((72, 72), "Maternal effect differs from maternal inheritance")
            doc.save(str(pdf))
            doc.close()
            pages = source_pages.load_source_pages(art)
            self.assertIsNotNone(pages)
            self.assertEqual(len(pages), 2)
            self.assertIn("Chloroplast", pages[0]["text"])
            self.assertTrue((art / "source_pages.json").is_file())
            # Cached load must return the same page text.
            again = source_pages.load_source_pages(art)
            self.assertEqual(again[1]["text"], pages[1]["text"])


if __name__ == "__main__":
    unittest.main()
