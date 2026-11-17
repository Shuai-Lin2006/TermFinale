"""Round 17: 10-page figure sample, captions, render height."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from PIL import Image

from tfv2.render.docx import MAX_FIGURE_HEIGHT_CM


class FigureFitTests(unittest.TestCase):
    def test_ten_page_sample_captions_and_height(self):
        base = Path("docs/evidence/v2_ring_full")
        sections = json.loads((base / "sections.json").read_text(encoding="utf-8"))
        rows = []
        for sec in sections:
            for block in sec.get("blocks") or []:
                fig = block.get("figure")
                if not fig:
                    continue
                page = (fig.get("source") or {}).get("page_start")
                if page and int(page) > 10:
                    continue
                rows.append(fig)
        self.assertGreaterEqual(len(rows), 3)
        for fig in rows:
            self.assertTrue(str(fig.get("caption") or "").strip())
            path = base / str(fig.get("asset_path") or "")
            self.assertTrue(path.is_file())
            with Image.open(path) as im:
                w, h = im.size
            # Word: max width 9.5cm / max height 6.5cm; A4 height 29.7cm.
            word_h = min(MAX_FIGURE_HEIGHT_CM, 9.5 * h / max(1, w))
            self.assertLessEqual(word_h / 29.7, 0.25)
            # HTML: max-width 560px / max-height 220px; A4 height ~1123px.
            html_h = min(220, 560 * h / max(1, w))
            self.assertLessEqual(html_h / 1123, 0.25)


if __name__ == "__main__":
    unittest.main()
