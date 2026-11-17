"""MinerU markdown and routing."""
from __future__ import annotations
import unittest
from tfv2.ingest.mineru_router import mineru_ledger, route_pages
from tfv2.domain.page import Page, PageLedger, PageQuality


def ledger(text):
    return PageLedger(material="x", page_count=1, source_hash="d", parser_version="d",
                      pages=[Page(material="x", page_no=1, text=text, quality=PageQuality.OCR)])


class Tests(unittest.TestCase):
    def test_mineru(self):
        md = "<!-- page 1 of 1 -->\n正文\n![Image block](a)\n![Formula block](b)\n"
        l = mineru_ledger(md)
        self.assertEqual(l.page_count, 1)
        self.assertEqual(len(l.pages[0].images), 1)
        self.assertTrue(l.pages[0].formula_damage)

    def test_route_formula(self):
        d = ledger("普通")
        m = mineru_ledger("<!-- page 1 of 1 -->\n" + "很长的公式页正文" * 12 + "\n![Formula block](x)")
        r = route_pages(d, m)
        self.assertEqual(r.parser_version, "router-v2")
        self.assertIn("普通", r.pages[0].text)


if __name__ == "__main__":
    unittest.main()
