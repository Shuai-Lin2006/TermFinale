"""v2 PPTX 页账本测试。"""
from __future__ import annotations

import base64
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

from tfv2.domain.page import PageQuality
from tfv2.ingest.pptx import build_pptx_page_ledger

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def add_text(slide, lines: list[str]) -> None:
    box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(8), Inches(3))
    tf = box.text_frame
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line


class PptxIngestTests(unittest.TestCase):
    def test_builds_all_pages_and_cleans_slide_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            pptx_path = td_path / "环烃.pptx"
            prs = Presentation()
            s1 = prs.slides.add_slide(prs.slide_layouts[6])
            add_text(s1, ["第四章 环烃", "一、脂环烃 二、芳香烃"])
            s2 = prs.slides.add_slide(prs.slide_layouts[6])
            add_text(s2, ["4.1 脂环烃", "一、分类", "二、结构", "<number>", "11/09/26"])
            s3 = prs.slides.add_slide(prs.slide_layouts[6])
            s3.shapes.add_picture(BytesIO(_PNG), Inches(1), Inches(1), width=Inches(1))
            prs.save(pptx_path)

            ledger = build_pptx_page_ledger(pptx_path, image_dir=td_path / "assets")
            self.assertEqual(ledger.page_count, 3)
            self.assertEqual([p.page_no for p in ledger.pages], [1, 2, 3])
            self.assertNotIn("<number>", ledger.pages[1].text)
            self.assertNotIn("11/09/26", ledger.pages[1].text)
            self.assertEqual(ledger.pages[2].quality, PageQuality.IMAGE_ONLY)
            self.assertEqual(len(ledger.pages[2].images), 1)
            self.assertTrue(Path(ledger.pages[2].images[0].asset_path).is_file())
            self.assertAlmostEqual(ledger.coverage, 1.0)

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            build_pptx_page_ledger("/tmp/does-not-exist-tfv2.pptx")


if __name__ == "__main__":
    unittest.main()
