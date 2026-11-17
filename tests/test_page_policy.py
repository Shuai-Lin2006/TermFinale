"""Page range + page-count policy."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pymupdf

from tfv2.product import page_policy, page_scope


class PagePolicyTests(unittest.TestCase):
    def test_precise_mandatory_under_100(self):
        info = page_policy.options(100)
        self.assertEqual(info["required"], "precise")
        self.assertEqual([x["mode"] for x in info["choices"]], ["precise"])

    def test_100_page_eta_matches_measured_run(self):
        p = page_policy.options(100)["choices"][0]
        self.assertGreaterEqual(p["time_min_minutes"], 25)
        self.assertLessEqual(p["time_max_minutes"], 45)
        self.assertIn("31", page_policy.options(100)["warning"])

    def test_choices_100_to_500(self):
        info = page_policy.options(300)
        self.assertEqual([x["mode"] for x in info["choices"]], ["precise", "approx"])
        self.assertIn("更慢", info["warning"])

    def test_1000_warns(self):
        info = page_policy.options(1001)
        self.assertEqual(len(info["choices"]), 2)
        self.assertIn("很高", info["warning"])


class PageScopeTests(unittest.TestCase):
    def test_parse_and_slice(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "s.pdf"
            doc = pymupdf.open()
            for i in range(10):
                doc.new_page().insert_text((72, 72), f"page {i+1}")
            doc.save(str(src)); doc.close()
            self.assertEqual(page_scope.parse("1-3,5", 10), [1, 2, 3, 5])
            out = Path(td) / "o.pdf"
            info = page_scope.slice_pdf(src, out, "1-3,5")
            self.assertEqual(info["page_count"], 4)
            d = pymupdf.open(str(out)); self.assertEqual(len(d), 4); d.close()

    def test_bad_range(self):
        with self.assertRaises(page_scope.ScopeError):
            page_scope.parse("0-2", 10)
        with self.assertRaises(page_scope.ScopeError):
            page_scope.parse("5-2", 10)


if __name__ == "__main__":
    unittest.main()
