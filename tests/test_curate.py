"""Fact curation must remove figure-only/duplicates."""
from __future__ import annotations
import unittest
from tfv2.canonical.curate import curate_facts
from tfv2.canonical.model import Fact, FactKind


class Tests(unittest.TestCase):
    def test_drop(self):
        rows = [
            Fact(fact_id="a", page=1, kind=FactKind.FIGURE, text="电路如图6-14所示。"),
            Fact(fact_id="b", page=1, kind=FactKind.DEFINITION, text="放大倍数是指输出与输入之比。"),
            Fact(fact_id="c", page=1, kind=FactKind.DEFINITION, text="放大倍数是指输出与输入之比。"),
        ]
        out = curate_facts(rows)
        self.assertEqual([x.fact_id for x in out], ["b"])

    def test_per_page_cap(self):
        rows = [Fact(fact_id=str(i), page=1, kind=FactKind.DEFINITION, text=f"定义：这是第{i}条足够长的事实内容。") for i in range(12)]
        self.assertEqual(len(curate_facts(rows, per_page=8)), 8)


if __name__ == "__main__": unittest.main()
