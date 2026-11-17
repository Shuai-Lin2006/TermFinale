"""Slot generation must never silently drop a fact."""
from __future__ import annotations

import unittest

from tfv2.canonical.generate import generate_slots
from tfv2.canonical.model import CanonicalDocument, Fact, FactKind


class Fake:
    def __init__(self, skip=None): self.skip = skip or set()
    def json(self, system, user, **kwargs):
        import json
        payload = json.loads(user.split("\n", 1)[1])
        return {"blocks": [{"fact_id": x["fact_id"], "text": "讲解 " + x["text"]}
                           for x in payload if x["fact_id"] not in self.skip]}


def doc():
    return CanonicalDocument(document_id="d", material="m", page_count=1, facts=[
        Fact(fact_id="f1", page=1, kind=FactKind.DEFINITION, text="定义甲"),
        Fact(fact_id="f2", page=1, kind=FactKind.FORMULA, text="公式乙"),
    ])


class SlotTests(unittest.TestCase):
    def test_all_consumed(self):
        r = generate_slots(doc(), Fake())
        self.assertEqual(r.status, "validated")
        self.assertEqual(r.coverage, 1.0)
        self.assertEqual(len(r.blocks), 2)

    def test_missing_is_partial(self):
        r = generate_slots(doc(), Fake(skip={"f2"}))
        self.assertEqual(r.status, "partial")
        self.assertEqual(r.missing, ["f2"])


if __name__ == "__main__":
    unittest.main()
