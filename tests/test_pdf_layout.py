"""Round 19: PDF layout constants + 24-page sample checks."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

import pymupdf

from tfv2.render.lecture_html import render_lecture_html


class PrintLayoutTests(unittest.TestCase):
    def test_print_css_has_orphan_and_figure_rules(self):
        html = render_lecture_html.__globals__["CSS"] if "CSS" in render_lecture_html.__globals__ else ""
        # CSS lives in the module; read it through a rendered document instead.
        spec = __import__("tests.test_tfv2_lecture", fromlist=["make_spec"]).make_spec()
        html = render_lecture_html(spec)
        for marker in ("orphans:3", "widows:3", "break-inside:avoid",
                       "figure img{max-height:60mm", "thead{display:table-header-group"):
            self.assertIn(marker, html, marker)

    def test_24_page_pdf_has_no_blank_page_and_small_figures(self):
        path = Path(os.path.expanduser(
            "~/Library/Application Support/TermFinale/v3-data/artifacts/gen_20261114_200319_66ad2a/lecture.pdf"))
        if not path.is_file():
            self.skipTest("24-page sample artifact not present")
        doc = pymupdf.open(str(path))
        try:
            self.assertGreaterEqual(len(doc), 1)
            for page in doc:
                self.assertGreaterEqual(len(page.get_text().strip()), 20)
            ratios = []
            for page in doc:
                for img in page.get_images(full=True):
                    try:
                        bbox = page.get_image_bbox(img)
                        ratios.append((bbox.y1 - bbox.y0) / page.rect.height)
                    except Exception:
                        continue
            self.assertTrue(all(r <= 0.25 for r in ratios), ratios)
        finally:
            doc.close()


if __name__ == "__main__":
    unittest.main()
