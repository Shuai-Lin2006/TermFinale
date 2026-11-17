"""Per-file planning never aggregates page counts."""
from __future__ import annotations
import unittest
from tfv2.product.job_plan import FileSpec, build_plan
from tfv2.product.scale_policy import DetailMode


class Tests(unittest.TestCase):
    def test_per_file(self):
        p = build_plan([FileSpec(name="A", pages=40), FileSpec(name="B", pages=40)])
        self.assertEqual([x.size for x in p.files], ["small", "small"])
        self.assertEqual([x.coverage for x in p.files], [1.0, 1.0])
        self.assertEqual(p.total_minutes, sum(x.minutes for x in p.files))

    def test_large_confirm(self):
        p = build_plan([FileSpec(name="C", pages=300)], mode=DetailMode.FULL)
        self.assertTrue(p.requires_confirm)
        self.assertEqual(p.files[0].preview_range, "1-2")

    def test_parallel_cap(self):
        p = build_plan([FileSpec(name=str(i), pages=10) for i in range(20)], parallel_workers=16)
        self.assertLessEqual(p.parallel_workers, 8)


if __name__ == "__main__":
    unittest.main()
