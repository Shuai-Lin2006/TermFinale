"""Teaching contract: roles and anchors both required."""
from __future__ import annotations
import unittest
from tfv2.canonical.model import Fact, FactKind, SectionPlan
from tfv2.canonical.teach import required_roles, synthesize_teaching


class Fake:
    def __init__(self, roles): self.roles = roles
    def json(self, *a, **k):
        return {"blocks": [{"role": r, "text": "x", "covers": ["f1"]} for r in self.roles]}


class Tests(unittest.TestCase):
    def test_complete(self):
        plan = SectionPlan(plan_id="p", page_start=1, page_end=1, fact_ids=["f1"])
        facts = [Fact(fact_id="f1", page=1, kind=FactKind.DEFINITION, text="甲")]
        roles = [r.value for r in required_roles(facts)]
        r = synthesize_teaching(plan, facts, Fake(roles))
        self.assertEqual(r.status, "validated")
        self.assertEqual(r.missing_roles, [])

    def test_missing_role(self):
        plan = SectionPlan(plan_id="p", page_start=1, page_end=1, fact_ids=["f1"])
        facts = [Fact(fact_id="f1", page=1, kind=FactKind.DEFINITION, text="甲")]
        r = synthesize_teaching(plan, facts, Fake(["definition"]))
        self.assertEqual(r.status, "partial")
        self.assertTrue(r.missing_roles)


if __name__ == "__main__": unittest.main()
