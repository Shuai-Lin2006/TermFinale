"""标题层：MinerU 标题 → 真实章节目录，没有标题要老实降级。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.product import headings as H


class HeadingTests(unittest.TestCase):
    def test_load_missing_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(H.load_headings(Path(td)), [])
        self.assertEqual(H.load_headings(None), [])

    def test_load_and_normalize_merges_chapter_titles(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "headings.json").write_text(json.dumps({"headings": [
                {"page": 2, "level": 2, "text": "1.3.4 三极管的特性曲线"},
                {"page": 10, "level": 2, "text": "第二章"},
                {"page": 10, "level": 2, "text": "放大电路分析基础"},
                {"page": 10, "level": 2, "text": "放大电路分析基础"},
            ]}, ensure_ascii=False), encoding="utf-8")
            rows = H.normalize_headings(H.load_headings(root))
        texts = [x["text"] for x in rows]
        self.assertIn("第二章 放大电路分析基础", texts)
        self.assertEqual(texts.count("放大电路分析基础"), 0, "被合并过的标题不应重复出现")

    def test_chapters_cover_every_selected_page_once(self) -> None:
        heads = [{"page": 3, "level": 1, "text": "第一章 极限"},
                 {"page": 7, "level": 1, "text": "第二章 导数"}]
        chapters = H.chapters_from_headings(heads, list(range(1, 11)))
        pages = [p for c in chapters for p in c["pages"]]
        self.assertEqual(sorted(pages), list(range(1, 11)))
        self.assertEqual(len(pages), len(set(pages)))
        self.assertEqual(chapters[0]["title"], "开篇（第 1 页起）")
        self.assertEqual(chapters[1]["title"], "第一章 极限")
        self.assertEqual(chapters[2]["title"], "第二章 导数")

    def test_no_headings_falls_back_to_page_ranges(self) -> None:
        chapters = H.chapters_from_headings([], list(range(1, 31)), chunk=10)
        self.assertEqual([c["title"] for c in chapters], ["第 1–10 页", "第 11–20 页", "第 21–30 页"])

    def test_long_chapter_is_split_with_page_suffix(self) -> None:
        heads = [{"page": 1, "level": 1, "text": "第一章 极限"}]
        chapters = H.chapters_from_headings(heads, list(range(1, 61)), chunk=25)
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0]["title"], "第一章 极限")
        self.assertIn("第 26–50 页", chapters[1]["title"])

    def test_headings_outside_selection_ignored(self) -> None:
        heads = [{"page": 50, "level": 1, "text": "第三章 积分"}]
        chapters = H.chapters_from_headings(heads, [1, 2, 3])
        self.assertEqual([c["pages"] for c in chapters], [[1, 2, 3]])


class ItemHeadingTests(unittest.TestCase):
    def test_list_items_dropped_when_chapter_numbers_exist(self) -> None:
        heads = [{"page": 1, "level": 2, "text": "1.3.4 三极管的特性曲线"},
                 {"page": 1, "level": 2, "text": "1. 输入特性"},
                 {"page": 2, "level": 2, "text": "1.3.5 三极管的主要参数"},
                 {"page": 2, "level": 2, "text": "2. 输出特性"},
                 {"page": 3, "level": 2, "text": "第二章 放大电路"}]
        rows = H.normalize_headings(heads)
        texts = [x["text"] for x in rows]
        self.assertIn("1.3.4 三极管的特性曲线", texts)
        self.assertNotIn("1. 输入特性", texts)
        self.assertNotIn("2. 输出特性", texts)

    def test_list_items_kept_when_no_chapter_numbers(self) -> None:
        heads = [{"page": 1, "level": 2, "text": "1. 极限"}, {"page": 2, "level": 2, "text": "2. 导数"}]
        self.assertEqual([x["text"] for x in H.normalize_headings(heads)], ["1. 极限", "2. 导数"])
