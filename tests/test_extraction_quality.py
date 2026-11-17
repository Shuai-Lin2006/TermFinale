
"""Round 10: extraction quotes + near-duplicate merge."""
from __future__ import annotations

import unittest

from tfv2.product import tasks


class ExtractionQualityTests(unittest.TestCase):
    def test_near_duplicate_points_are_merged(self):
        items = [
            {"point": "导数定义", "detail": "瞬时变化率", "quote": "导数表示瞬时变化率。", "page": 1},
            {"point": "导数的定义", "detail": "瞬时变化率", "quote": "导数表示瞬时变化率。", "page": 2},
        ]
        kept, merged = tasks._dedupe_items(items, "extract_points")
        self.assertEqual(len(kept), 1)
        self.assertEqual(merged, 1)
        self.assertEqual(kept[0]["page_end"], 2)

    def test_best_quote_comes_from_source(self):
        page_text = {1: "导数表示瞬时变化率。连续不一定可导。"}
        quote = tasks._best_quote("导数定义 瞬时变化率", page_text, [1])
        self.assertIn("导数", quote)
        self.assertTrue(tasks._quote_valid(quote, page_text, [1]))

    def test_wrong_quote_is_rejected(self):
        page_text = {1: "导数表示瞬时变化率。"}
        self.assertFalse(tasks._quote_valid("这段话不在原文里，完全编造。", page_text, [1]))


if __name__ == "__main__":
    unittest.main()
