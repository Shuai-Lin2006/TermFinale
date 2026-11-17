"""多资料权重：切分大小和页码范围必须可预测。"""
from __future__ import annotations

import unittest

from tfv2.product import multi


class MultiTests(unittest.TestCase):
    def test_high_weight_gets_finer_chunks(self) -> None:
        self.assertLess(multi._cn_size(5), multi._cn_size(1))
        self.assertGreaterEqual(multi._cn_size(5), 4)
        self.assertLessEqual(multi._cn_size(1), 12)

    def test_plan_covers_ranges_and_keeps_weights(self) -> None:
        plan = multi._plan([
            {"name": "A.pdf", "weight": 5, "start": 1, "end": 5},
            {"name": "B.pdf", "weight": 1, "start": 6, "end": 20},
        ])
        self.assertEqual([p for _, pages, _, _ in plan for p in pages], list(range(1, 21)))
        self.assertTrue(all("A.pdf" in label and w == 5 for label, _, _, w in plan if "A.pdf" in label))
        self.assertTrue(all("B.pdf" in label and w == 1 for label, _, _, w in plan if "B.pdf" in label))


if __name__ == "__main__":
    unittest.main()
