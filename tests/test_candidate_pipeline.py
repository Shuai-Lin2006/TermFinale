"""Round 4: candidate-first batch verification."""
from __future__ import annotations

import unittest

from tfv2.product import candidate_pipeline


class FakeClient:
    def json(self, system, user, **kwargs):
        return {"items": [{"id": 1, "page": 1, "point": "导数定义", "detail": "瞬时变化率",
                           "quote": "导数的定义：函数在某点的瞬时变化率。"}]}


class FailClient:
    def json(self, *a, **k):
        raise RuntimeError("api down")


class CandidatePipelineTests(unittest.TestCase):
    def test_model_accepts_candidate(self):
        text = {1: "导数的定义：函数在某点的瞬时变化率。", 2: "极限的定义：数列无限接近某个确定的常数。"}
        out = candidate_pipeline.verify_points(FakeClient(), text, [1, 2], batch_pages=2)
        self.assertEqual(out["pages"], 2)
        self.assertGreaterEqual(out["model_pages"], 1)
        self.assertTrue(any(x.get("verified") for x in out["items"]))
        self.assertEqual(out["missing_pages"], [])

    def test_api_failure_keeps_local_candidates(self):
        text = {1: "导数的定义：函数在某点的瞬时变化率。"}
        out = candidate_pipeline.verify_points(FailClient(), text, [1], batch_pages=1)
        self.assertEqual(out["model_pages"], 0)
        self.assertEqual(out["local_only_pages"], 1)
        self.assertTrue(out["items"][0].get("local_only"))
        self.assertEqual(out["fallback_percent"], 100.0)


if __name__ == "__main__":
    unittest.main()
