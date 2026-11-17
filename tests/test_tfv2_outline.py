"""v2 大纲：人工确认大纲的加载/校验。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.curriculum.outline import CourseOutline, OutlineError, load_outline, save_outline

ROOT = Path(__file__).resolve().parents[1]
RING = ROOT / "tfv2" / "examples" / "ring_4_1_outline.json"
FULL = ROOT / "tfv2" / "examples" / "ring_full_outline.json"


class OutlineIoTests(unittest.TestCase):
    def test_load_ring_outline(self) -> None:
        outline = load_outline(RING)
        self.assertEqual(outline.chapter_title, "第四章 环烃")
        self.assertEqual(outline.page_count, 50)
        self.assertEqual([s.title for s in outline.sections], ["本章导览", "4.1 脂环烃", "4.2 芳香烃"])
        sec = outline.sections[1]
        self.assertEqual(sec.pages, list(range(2, 19)))
        self.assertEqual(len(sec.subsections), 6)
        self.assertEqual(sec.subsections[2].title, "二、环烷烃的结构")
        self.assertEqual(sec.subsections[2].pages, [6, 7, 8])

    def test_full_outline_covers_all_50_pages(self) -> None:
        outline = load_outline(FULL)
        self.assertEqual(len(outline.sections), 3)
        pages = [p for s in outline.sections for p in s.pages]
        self.assertEqual(pages, list(range(1, 51)))
        sec42 = outline.sections[2]
        self.assertEqual(len(sec42.subsections), 7)
        self.assertEqual(sec42.subsections[1].pages, [20, 25, 26, 30])
        self.assertEqual(sec42.subsections[2].pages, [21, 22, 23, 24])
        self.assertEqual(sec42.subsections[3].pages, [27, 28, 29])

    def test_invalid_outline_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text(json.dumps({
                "chapter_title": "坏大纲",
                "page_count": 3,
                "source": "manual",
                "sections": [{
                    "title": "一节",
                    "pages": [1, 2],
                    "subsections": [{"title": "正文", "pages": [1]}],
                }],
            }), encoding="utf-8")
            with self.assertRaises(OutlineError):
                load_outline(p)

    def test_save_roundtrip(self) -> None:
        outline = load_outline(RING)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "outline.json"
            save_outline(outline, p)
            again = load_outline(p)
            self.assertEqual(outline.model_dump(), again.model_dump())


if __name__ == "__main__":
    unittest.main()
