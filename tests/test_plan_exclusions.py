
"""User 'not tested' instructions must remove sections before authoring."""
from __future__ import annotations

import unittest

from tfv2.product.generate import _excluded_terms, _filter_plan


class PlanExclusionTests(unittest.TestCase):
    def test_excluded_topic_removes_section_and_pages(self) -> None:
        plan = [("第三章 积分", [1, 2]), ("第四章 微分", [3, 4])]
        text = {1: "积分中值定理", 2: "积分", 3: "导数", 4: "微分"}
        kept, pages = _filter_plan(plan, text, ["积分中值定理"])
        self.assertEqual([x[0] for x in kept], ["第四章 微分"])
        self.assertEqual(pages, {1, 2})

    def test_label_match_removes_section(self) -> None:
        plan = [("第三章 不考章节", [1, 2]), ("第四章 微分", [3])]
        kept, pages = _filter_plan(plan, {1: "x", 2: "y", 3: "z"}, ["第三章"])
        self.assertEqual([x[0] for x in kept], ["第四章 微分"])
        self.assertEqual(pages, {1, 2})

    def test_no_terms_keeps_plan(self) -> None:
        plan = [("a", [1])]
        kept, pages = _filter_plan(plan, {1: "x"}, [])
        self.assertEqual(kept, plan)
        self.assertEqual(pages, set())

    def test_requirements_terms(self) -> None:
        terms = _excluded_terms({"must_not": [{"label": "积分中值定理"}]}, "极限\n")
        self.assertIn("积分中值定理", terms)
        self.assertIn("极限", terms)


if __name__ == "__main__":
    unittest.main()
