"""课程紧迫度/优先级评估。

v2 模型（可解释、可标定）：
    需求量 D = 学分 × 12 × (主观难度/3) × 目标系数
    可用量 A = 剩余天数 × 每日可用小时
    负载   L = D / A
    压力   S = L / (1 + L)          # 0~1，负载越高越接近 1
    硬度   H = 课程硬度 / 100
    差距   G = max(0, 目标分 - 预估分) / 60
    权重   = 100 × (0.45S + 0.35H + 0.20G)

旧模型是 `硬度×0.4 + 紧迫度×0.6`，而紧迫度在 ≤3 天直接给 100、
≤7 天给 85~100 —— 结果几乎所有临考课程都顶格（实测 100/100/91），区分度消失。
新模型里"天数越多权重越低"，单调性由 `tests/test_weights.py` 守住。
"""
from __future__ import annotations

DEFAULT_DAILY_HOURS = 4.0


class CourseInfo:
    def __init__(self, name: str, school_level: str, major: str, is_core_major: bool,
                 credits: float, days_left: int, target_score: int, user_difficulty: int):
        self.name = name
        self.school_level = school_level
        self.major = major
        self.is_core_major = is_core_major
        self.credits = max(0.5, min(10.0, float(credits)))
        self.days_left = max(1, int(days_left))
        self.target_score = max(0, min(100, int(target_score)))
        self.user_difficulty = max(1, min(5, int(user_difficulty)))

    # ------------------------------------------------------------------ #
    def course_hardness(self) -> float:
        """课程绝对硬度 0~100：学分 + 是否专业课 + 学校层级 + 主观难度。"""
        credit_base = min(40.0, self.credits * 8.0)
        major_base = 30.0 if self.is_core_major else 10.0

        school_factor = {"985": 1.0, "211": 0.9, "普通一本": 0.8, "普通二本": 0.6, "专科": 0.4}
        base_school_val = school_factor.get(self.school_level, 0.8) * 15

        # 难度非线性放大：3 星为基准，4 星 1.5 倍，5 星 2 倍
        if self.user_difficulty >= 3:
            diff_multiplier = 1.0 + (self.user_difficulty - 3) * 0.5
        else:
            diff_multiplier = 1.0 - (3 - self.user_difficulty) * 0.2
        diff_val = min(15.0, 15 * diff_multiplier)

        return min(100.0, credit_base + major_base + base_school_val + diff_val)

    def required_hours(self) -> float:
        """达到目标分大概需要多少小时。"""
        base = self.credits * 12 * (self.user_difficulty / 3.0)
        score_multiplier = 1.0 + (self.target_score - 60) / 100.0  # 60→1.0，100→1.4
        return max(1.0, base * score_multiplier)

    # ------------------------------------------------------------------ #
    def evaluate(self, daily_hours: float = DEFAULT_DAILY_HOURS) -> dict:
        daily_hours = max(0.5, float(daily_hours))

        hardness = self.course_hardness()
        required = self.required_hours()
        available = max(1.0, self.days_left * daily_hours)

        load = required / available
        stress = load / (1.0 + load)                 # 0~1
        hardness_norm = hardness / 100.0

        time_ratio = available / required
        predicted = max(30.0, min(100.0, 40.0 + 60.0 * min(1.0, time_ratio)))
        gap = max(0.0, self.target_score - predicted) / 60.0

        weight = 100.0 * (0.45 * stress + 0.35 * hardness_norm + 0.20 * min(1.0, gap))
        weight = max(0.0, min(100.0, weight))

        if time_ratio < 0.5:
            status = "极度危险"
        elif time_ratio < 1.0:
            status = "时间紧迫"
        else:
            status = "安全充裕"

        raw_daily = required / self.days_left * 1.3            # 留 30% 余量
        suggested_daily = min(12.0, max(0.5, round(raw_daily * 2) / 2))

        advice = [f"需要约 {required:.0f} 小时，可用 {available:.0f} 小时（每天 {daily_hours:g} 小时）"]
        if load > 1.0:
            advice.append(f"缺口约 {required - available:.0f} 小时：只保必考章节，放弃冷门推导")
        else:
            advice.append(f"时间够用：建议每天投入 {required / self.days_left:.1f} 小时，可深挖原理")
        if self.target_score >= 90 and predicted < self.target_score:
            if raw_daily > 12:
                advice.append(
                    f"目标 {self.target_score} 分不现实：即使每天 12 小时也要 {required / 12:.0f} 天，"
                    f"建议把目标下调到 {max(60.0, min(95.0, predicted + 10)):.0f} 分左右"
                )
            else:
                advice.append(f"目标 {self.target_score} 分偏高：按当前时间预估约 {predicted:.0f} 分，"
                              f"建议每天加到 {suggested_daily:g} 小时")

        if status == "极度危险":
            warning_msg = (f"🚨 绝对危机：需 {required:.0f} 小时，只剩 {available:.0f} 小时，"
                           f"预计得分约 {predicted:.0f} 分。立刻放弃推导，只背核心公式！")
        elif status == "时间紧迫":
            warning_msg = "⚠️ 高危预警：任务量超出可用时间，建议抓大放小，战略性放弃冷门章节。"
        else:
            warning_msg = (f"✅ 时间充足：建议每天投入 {required / self.days_left:.1f} 小时，"
                           f"可深挖原理冲击高分。")

        return {
            # 兼容旧接口
            "course_hardness": round(hardness, 1),
            "urgency_score": round(stress * 100, 1),
            "final_priority_weight": round(weight, 1),
            "required_hours": round(required, 1),
            "available_hours": round(available, 1),
            "status": status,
            "warning_msg": warning_msg,
            # v2 新增
            "load": round(load, 2),
            "stress": round(stress, 3),
            "predicted_score": round(predicted, 1),
            "suggested_daily_hours": suggested_daily,
            "advice": advice,
        }
