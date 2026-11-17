"""Canonical pipeline must plan every extracted fact."""
from __future__ import annotations

import unittest

from tfv2.canonical.pipeline import plan_sections, run_canonical
from tfv2.domain.page import Page, PageLedger, PageQuality


def ledger(text: str) -> PageLedger:
    return PageLedger(material="x", page_count=1, source_hash="h", parser_version="test",
                      pages=[Page(material="x", page_no=1, text=text, quality=PageQuality.OCR)])


class CanonicalTests(unittest.TestCase):
    def test_all_facts_planned(self):
        doc = run_canonical(ledger("定义：放大倍数是指输出与输入之比。因此输出增大。注意不能忽略负载。"))
        self.assertTrue(doc.facts)
        self.assertEqual(doc.coverage, 1.0)
        self.assertEqual(doc.status, "validated")
        self.assertEqual(len(doc.plans), 1)

    def test_empty_is_partial(self):
        doc = run_canonical(ledger(""))
        self.assertEqual(doc.facts, [])
        self.assertEqual(doc.status, "partial")

    def test_plan_sections_cover_all(self):
        doc = run_canonical(ledger("定义：x是指y。因此成立。注意不能错。"))
        planned = {f for p in plan_sections(doc.facts) for f in p.fact_ids}
        self.assertEqual(planned, {f.fact_id for f in doc.facts})


if __name__ == "__main__":
    unittest.main()
