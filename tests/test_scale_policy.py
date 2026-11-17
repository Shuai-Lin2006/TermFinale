"""Scale policy: coverage thresholds and per-file estimates."""
from __future__ import annotations
import unittest
from tfv2.product.scale_policy import DetailMode, SizeClass, coverage_target, estimate, per_file_estimates, size_class


class Tests(unittest.TestCase):
    def test_coverage(self):
        self.assertEqual(coverage_target(50), 1.0)
        self.assertEqual(coverage_target(51), 0.90)
        self.assertEqual(coverage_target(100), 0.90)
        self.assertEqual(coverage_target(101), 0.85)
        self.assertEqual(coverage_target(150), 0.85)
        self.assertEqual(coverage_target(151), 0.80)

    def test_size(self):
        self.assertEqual(size_class(50), SizeClass.SMALL)
        self.assertEqual(size_class(51), SizeClass.MEDIUM)
        self.assertEqual(size_class(151), SizeClass.XLARGE)

    def test_per_file_not_summed(self):
        rows = per_file_estimates([("a", 40), ("b", 40)])
        self.assertEqual([x["size"] for x in rows], [SizeClass.SMALL, SizeClass.SMALL])

    def test_preview(self):
        e = estimate(80, mode=DetailMode.FULL, preview_pages=3)
        self.assertEqual(e.preview_pages, 3)
        self.assertTrue(e.requires_confirm())


if __name__ == "__main__":
    unittest.main()
