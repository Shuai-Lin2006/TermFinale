import unittest
from tfv2.product.lecture_tiers import MaterialInput, plan_materials, tiers_for_pages


class LectureTierTests(unittest.TestCase):
    def test_rules_are_by_single_material_pages(self):
        self.assertEqual(tiers_for_pages(50), ["standard"])
        self.assertEqual(tiers_for_pages(51), ["premium", "broad"])
        self.assertEqual(tiers_for_pages(150), ["premium", "broad"])
        self.assertEqual(tiers_for_pages(151), ["normal", "premium", "broad"])
        self.assertEqual(tiers_for_pages(500), ["normal", "premium", "broad"])
        self.assertEqual(tiers_for_pages(501), ["normal", "premium"])

    def test_pages_can_be_any_subset(self):
        plan = plan_materials([MaterialInput("a", 40, [3, 1, 2])])
        self.assertEqual(plan["materials"][0]["pages"], [1, 2, 3])
        self.assertEqual(plan["materials"][0]["tiers"], ["standard"])

    def test_merge_intersects_tiers_and_rejects_empty(self):
        ok = plan_materials([
            MaterialInput("a", 80),
            MaterialInput("b", 200),
        ], merge=True)
        self.assertEqual(ok["merge_tiers"], ["premium", "broad"])
        with self.assertRaises(ValueError):
            plan_materials([MaterialInput("a", 20), MaterialInput("b", 80)], merge=True)

    def test_coverage_targets_are_written_in(self):
        cases = [
            (40, {"standard": 100}),
            (80, {"premium": 70, "broad": 85}),
            (200, {"normal": 50, "premium": 65, "broad": 75}),
            (600, {"normal": 50, "premium": 50}),
        ]
        for pages, targets in cases:
            got = plan_materials([MaterialInput("a", pages)])["materials"][0]["coverage_targets"]
            self.assertEqual(got, targets)
            m = plan_materials([MaterialInput("a", pages)])["materials"][0]
            self.assertTrue(m["no_omit"])
            self.assertTrue(m["guarantees"]["toc"])
            self.assertTrue(m["guarantees"]["summary"])
            self.assertEqual(m["guarantees"]["figures"], "best_effort")

    def test_no_merge_returns_one_plan_per_material(self):
        plan = plan_materials([MaterialInput("a", 20), MaterialInput("b", 80)], merge=False)
        self.assertFalse(plan["merge"])
        self.assertEqual(len(plan["materials"]), 2)


if __name__ == "__main__":
    unittest.main()
