"""Quality/cost tiers are estimates, not hidden model switches."""
from __future__ import annotations

import unittest

from tfv2.product import quality_tiers as qt


class TierTests(unittest.TestCase):
    def test_all_tiers_have_estimates(self):
        rows = qt.all_estimates(1000)
        self.assertEqual([x["tier"] for x in rows], ["eco", "balanced", "max"])
        for row in rows:
            self.assertGreater(row["cost_min_cny"], 0)
            self.assertGreater(row["time_min_minutes"], 0)
            self.assertEqual(row["page_coverage"], "100%")

    def test_max_costs_more_than_eco(self):
        rows = {x["tier"]: x for x in qt.all_estimates(1000)}
        self.assertGreater(rows["max"]["cost_max_cny"], rows["eco"]["cost_max_cny"])
        self.assertGreater(rows["max"]["time_max_minutes"], rows["eco"]["time_max_minutes"])

    def test_modules_reduce_cost(self):
        full = qt.estimate(1000, ["lecture", "extract", "exam"], "balanced")
        only = qt.estimate(1000, ["extract"], "balanced")
        self.assertLess(only["cost_max_cny"], full["cost_max_cny"])


if __name__ == "__main__":
    unittest.main()
