"""逐页账本：页数、文本、图片页、OCR 占位、引用必须分开。"""
from __future__ import annotations

import unittest

from core.quality.page_ledger import build_page_ledger, ledger_summary


class PageLedgerTest(unittest.TestCase):
    def test_classifies_pages(self):
        pages = [
            "【《x》第 1 页】\n足够长的正文内容，应该被标记为可用。" * 2,
            "【《x》第 2 页】\n[[[IMAGE:fig.png]]]\n短",
            "【《x》第 3 页】\n[本页 OCR 未识别出文字]",
            "【《x》第 4 页】\n另一页正文内容，但是没有被引用到生成物里。" * 2,
        ]
        md = "考点引用第 1 页"
        led = build_page_ledger(pages, md)
        self.assertEqual(led["pages"], 4)
        self.assertEqual(led["cited"], 1)
        self.assertEqual(led["missing_entries"], [])
        self.assertEqual(led["image_only"], [2])
        self.assertEqual(led["placeholder"], [3])
        self.assertEqual(led["uncited"], [2, 3, 4])
        self.assertEqual(led["status_counts"]["cited"], 1)
        self.assertEqual(led["status_counts"]["placeholder"], 1)

    def test_missing_page_entry_is_reported(self):
        led = build_page_ledger(["【《x》第 1 页】\n正文正文正文正文正文正文"], "", total=3)
        self.assertEqual(led["missing_entries"], [2, 3])
        self.assertEqual(led["accounted"], 1)

    def test_summary_omits_detail(self):
        led = build_page_ledger(["【《x》第 1 页】\n正文正文正文正文正文正文"], "第1页", total=1)
        s = ledger_summary(led)
        self.assertNotIn("detail", s)
        self.assertEqual(s["pages"], 1)
