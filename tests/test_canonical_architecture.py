"""Parser interface, module contract, orchestrator cache."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tfv2.canonical.contracts import ModuleResult, ModuleStatus, gate
from tfv2.canonical.orchestrator import CanonicalOrchestrator
from tfv2.canonical.parsers import DoclingStructureParser


class CountParser:
    name = "count"
    def __init__(self, inner): self.inner = inner; self.calls = 0
    def parse(self, source):
        self.calls += 1
        return self.inner.parse(source)


class Tests(unittest.TestCase):
    def setUp(self):
        self.data = {"pages": [{"page": 1, "blocks": [{"text": "定义：x是指y。因此成立。注意不能错。"}], "pictures": []}]}

    def test_parser_contract(self):
        ledger = DoclingStructureParser().parse(self.data)
        self.assertEqual(ledger.page_count, 1)

    def test_orchestrator_cache(self):
        with tempfile.TemporaryDirectory() as td:
            base = DoclingStructureParser(); parser = CountParser(base)
            orch = CanonicalOrchestrator(parser, td)
            a = orch.run(self.data, document_id="a")
            b = orch.run(self.data, document_id="a")
            self.assertEqual(parser.calls, 1)  # second run hits cache
            self.assertEqual(a.facts, b.facts)

    def test_gate(self):
        r = ModuleResult(module="lecture", status=ModuleStatus.PARTIAL, items=0, coverage=0)
        self.assertEqual(gate(r, min_items=1).status, ModuleStatus.PARTIAL)


if __name__ == "__main__":
    unittest.main()
