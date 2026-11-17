"""Anchor synthesis: free blocks, no missing anchors."""
from __future__ import annotations
import unittest
from tfv2.canonical.model import Fact, FactKind, SectionPlan
from tfv2.canonical.synthesize import synthesize_section


class Fake:
    def json(self, system, user, **kwargs):
        return {"blocks": [{"text": "连贯讲解", "covers": ["f1", "f2"]}]}


def data():
    facts = [Fact(fact_id="f1", page=1, kind=FactKind.DEFINITION, text="甲"),
             Fact(fact_id="f2", page=1, kind=FactKind.FORMULA, text="乙")]
    plan = SectionPlan(plan_id="p", page_start=1, page_end=1, fact_ids=["f1", "f2"])
    return plan, facts


class Tests(unittest.TestCase):
    def test_anchors(self):
        plan, facts = data(); r = synthesize_section(plan, facts, Fake())
        self.assertEqual(r.status, "validated")
        self.assertEqual(r.coverage, 1.0)

    def test_missing(self):
        plan, facts = data()
        class F:
            def json(self, *a, **k): return {"blocks": [{"text": "x", "covers": ["f1"]}]}
        r = synthesize_section(plan, facts, F())
        self.assertEqual(r.missing, ["f2"])
        self.assertEqual(r.status, "partial")


if __name__ == "__main__": unittest.main()
