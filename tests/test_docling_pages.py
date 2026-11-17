"""Docling page adapter must preserve pages, text and pictures."""
from __future__ import annotations

import unittest

from tfv2.ingest.docling_pages import pages_from_structure


class DoclingPagesTests(unittest.TestCase):
    def test_pages_text_pictures(self):
        data = {"pages": [{"page": 1, "blocks": [{"text": "第一页正文"}], "pictures": [{"bbox": [1, 2, 3, 4]}]}]}
        ledger = pages_from_structure(data)
        self.assertEqual(ledger.page_count, 1)
        self.assertEqual(ledger.pages[0].text, "第一页正文")
        self.assertEqual(len(ledger.pages[0].images), 1)


if __name__ == "__main__":
    unittest.main()
