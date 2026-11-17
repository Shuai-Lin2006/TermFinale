"""Token ledger: calls and tokens, no invented CNY cost."""
from __future__ import annotations

import unittest

from tfv2.llm import usage


class UsageTests(unittest.TestCase):
    def test_snapshot_accumulates(self):
        usage.reset()
        usage.add("deepseek", prompt_tokens=100, completion_tokens=50, total_tokens=150)
        usage.add("qwen", prompt_tokens=20, completion_tokens=10, total_tokens=30)
        snap = usage.snapshot()
        self.assertEqual(snap["calls"], 2)
        self.assertEqual(snap["total_tokens"], 180)
        self.assertEqual(snap["by_model"]["deepseek"]["tokens"], 150)


if __name__ == "__main__":
    unittest.main()
