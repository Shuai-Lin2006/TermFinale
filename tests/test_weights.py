"""权重模型的单调性与边界测试。

运行：.venv/bin/python -m tests.test_weights
"""
from __future__ import annotations

import unittest

from models.user_profile import CourseInfo


def make(**over):
    params = dict(name="物理", school_level="普通二本", major="环境工程", is_core_major=True,
                  credits=3.0, days_left=14, target_score=80, user_difficulty=3)
    params.update(over)
    return CourseInfo(**params)


def weight(**over) -> float:
    return make(**over).evaluate()["final_priority_weight"]


class WeightModelTest(unittest.TestCase):
    def test_days_monotonic(self):
        """天数越少 → 权重越高。旧模型在这里会顶格饱和。"""
        values = [weight(days_left=d) for d in (30, 21, 14, 7, 3, 1)]
        self.assertEqual(values, sorted(values), values)
        self.assertGreater(values[-1] - values[0], 10, values)

    def test_target_monotonic(self):
        values = [weight(target_score=t) for t in (60, 75, 90, 100)]
        self.assertEqual(values, sorted(values), values)

    def test_credits_monotonic(self):
        values = [weight(credits=c) for c in (1.0, 2.0, 4.0, 6.0)]
        self.assertEqual(values, sorted(values), values)

    def test_difficulty_monotonic(self):
        values = [weight(user_difficulty=d) for d in (1, 2, 3, 4, 5)]
        self.assertEqual(values, sorted(values), values)

    def test_bounds(self):
        for over in ({"days_left": 1, "target_score": 100, "credits": 6, "user_difficulty": 5},
                     {"days_left": 90, "target_score": 60, "credits": 1, "user_difficulty": 1}):
            value = weight(**over)
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)

    def test_no_saturation(self):
        """回归：三门课不应都显示 100 分。"""
        a = weight(days_left=1)
        b = weight(days_left=7)
        c = weight(days_left=30)
        self.assertGreater(a - b, 3, (a, b))
        self.assertGreater(b - c, 3, (b, c))

    def test_more_daily_hours_lowers_priority(self):
        info = make(days_left=7)
        self.assertGreater(info.evaluate(daily_hours=2)["final_priority_weight"],
                           info.evaluate(daily_hours=8)["final_priority_weight"])

    def test_report_fields(self):
        result = make().evaluate()
        for key in ("final_priority_weight", "status", "warning_msg", "advice",
                    "required_hours", "available_hours", "predicted_score"):
            self.assertIn(key, result)
        self.assertTrue(result["advice"])
        self.assertIn(result["status"], ("极度危险", "时间紧迫", "安全充裕"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
