"""Round 11: importance ranking + noun English/alias metadata."""
from __future__ import annotations

import unittest

from tfv2.product import delivery, tasks


class ImportanceTests(unittest.TestCase):
    def test_numeric_and_alias(self):
        self.assertEqual(tasks._importance(5), 5)
        self.assertEqual(tasks._importance("必背"), 5)
        self.assertEqual(tasks._importance("了解"), 2)
        self.assertEqual(tasks._importance("", "本章重点掌握"), 5)

    def test_label(self):
        self.assertEqual(tasks._importance_label(5), "必背")
        self.assertEqual(tasks._importance_label(2), "了解")


class NounMetaTests(unittest.TestCase):
    def test_abbreviation_and_english_from_term(self):
        meta = tasks._noun_meta({"term_en": "sympathetic nervous system",
                                 "abbreviation": "SNS"}, "交感神经系统（SNS）")
        self.assertEqual(meta["abbreviation"], "SNS")
        self.assertEqual(meta["term_en"], "sympathetic nervous system")

    def test_aliases_normalized(self):
        meta = tasks._noun_meta({"aliases": ["交感神经", "植物神经"]}, "交感神经")
        self.assertEqual(meta["aliases"], ["交感神经", "植物神经"])

    def test_missing_english_is_blank(self):
        self.assertEqual(tasks._noun_meta({}, "动作电位")["term_en"], "")


class FakeTranslate:
    def json(self, system, user, **kwargs):
        return {"items": [{"term": "动作电位", "term_en": "action potential", "abbreviation": "AP"}]}


class NounDeliveryTests(unittest.TestCase):
    def test_sparse_noun_coverage_is_not_a_delivery_defect(self):
        doc = {"kind": "extract_nouns", "status": "rejected",
               "issues": ["页覆盖 94.1% < 98%"],
               "coverage": {"coverage": 0.941, "pages": list(range(1, 35)),
                            "pages_cited": list(range(1, 34))},
               "content": {"items": [{"term": "导数", "definition": "瞬时变化率", "term_en": "derivative", "quote": "导数表示瞬时变化率"}]}}
        out = delivery.apply_task_delivery(dict(doc))
        self.assertEqual(out["status"], "validated")


class NounFillTests(unittest.TestCase):
    def test_missing_english_is_filled(self):
        items = [{"term": "动作电位", "term_en": "", "abbreviation": ""}]
        filled = tasks._fill_noun_english(items, FakeTranslate())
        self.assertEqual(filled, 1)
        self.assertEqual(items[0]["term_en"], "action potential")
        self.assertEqual(items[0]["abbreviation"], "AP")

    def test_existing_english_is_not_overwritten(self):
        items = [{"term": "动作电位", "term_en": "action potential"}]
        self.assertEqual(tasks._fill_noun_english(items, FakeTranslate()), 0)


if __name__ == "__main__":
    unittest.main()
