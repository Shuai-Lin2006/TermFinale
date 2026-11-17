"""v2 页账本测试：每一页都必须有账。"""
from __future__ import annotations

import unittest

from pydantic import ValidationError

from tfv2.domain.page import Page, PageLedger, PageQuality


def ledger(*pages: Page) -> PageLedger:
    return PageLedger(
        material="高数.pdf",
        page_count=len(pages),
        pages=list(pages),
        source_hash="sha256:test",
        parser_version="2.0",
    )


class PageLedgerTests(unittest.TestCase):
    def test_valid_ledger(self) -> None:
        x = ledger(
            Page(material="高数.pdf", page_no=1, text="第一页"),
            Page(material="高数.pdf", page_no=2, text="第二页"),
        )
        self.assertEqual(x.coverage, 1.0)

    def test_missing_page_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            PageLedger(
                material="高数.pdf",
                page_count=3,
                pages=[Page(material="高数.pdf", page_no=1, text="一")],
                source_hash="sha256:test",
                parser_version="2.0",
            )

    def test_duplicate_page_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            PageLedger(
                material="高数.pdf",
                page_count=2,
                pages=[
                    Page(material="高数.pdf", page_no=1, text="一"),
                    Page(material="高数.pdf", page_no=1, text="重复"),
                ],
                source_hash="sha256:test",
                parser_version="2.0",
            )

    def test_empty_page_counts_as_unreadable(self) -> None:
        x = ledger(
            Page(material="高数.pdf", page_no=1, text="一"),
            Page(material="高数.pdf", page_no=2, quality=PageQuality.EMPTY, missing_reason="空页"),
            Page(material="高数.pdf", page_no=3, text="三"),
        )
        self.assertAlmostEqual(x.coverage, 2 / 3, places=4)

    def test_image_only_page_still_accounted(self) -> None:
        x = ledger(
            Page(
                material="高数.pdf",
                page_no=1,
                quality=PageQuality.IMAGE_ONLY,
                images=[{"image_id": "img1", "caption": "图 1"}],
            )
        )
        self.assertEqual(x.coverage, 1.0)


if __name__ == "__main__":
    unittest.main()
