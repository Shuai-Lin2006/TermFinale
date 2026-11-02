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

    def evaluate(self) -> dict:
        # =======================================================
        # 模块一：课程绝对硬度 (满分 100)
        # =======================================================
        credit_base = min(40.0, self.credits * 8.0)
        major_base = 30 if self.is_core_major else 10

        school_factor = {"985": 1.0, "211": 0.9, "普通一本": 0.8, "普通二本": 0.6, "专科": 0.4}
        base_school_val = school_factor.get(self.school_level, 0.8) * 15
        # 🚨 难度非线性放大：3星为基准，4星1.5倍，5星2倍
        diff_multiplier = 1.0 + (self.user_difficulty - 3) * 0.5 if self.user_difficulty >= 3 else 1.0 - (
                    3 - self.user_difficulty) * 0.2
        diff_val = min(15.0, 15 * diff_multiplier)
        difficulty_base = base_school_val + diff_val

        course_hardness = credit_base + major_base + difficulty_base

        # =======================================================
        # 模块二：真实所需复习时间估算
        # =======================================================
        base_hours_needed = self.credits * 12 * (self.user_difficulty / 3.0)

        # 🚨 目标分数拉开差距：60分只需1.0倍，90分要1.5倍，100分要1.8倍！
        score_multiplier = 1.0 + ((self.target_score - 60) / 40.0) * 0.8
        required_hours = base_hours_needed * score_multiplier

        # =======================================================
        # 模块三：时间压力 (指数级爆炸)
        # =======================================================
        daily_limit = 4.0
        available_hours = self.days_left * daily_limit
        time_ratio = available_hours / required_hours

        # 🚨 紧迫度重构：如果天数少于7天，直接逼近满分
        if self.days_left <= 3:
            urgency_score = 100
        elif self.days_left <= 7:
            urgency_score = 85 + (7 - self.days_left) * 5
        else:
            urgency_score = min(80.0, 100.0 / (self.days_left * 0.2))

        # 最终调度权重
        final_priority_weight = (course_hardness * 0.4) + (urgency_score * 0.6)

        # =======================================================
        # 模块四：诊断报告
        # =======================================================
        warning_msg = ""
        status = ""

        if time_ratio < 0.5:
            status = "极度危险"
            pred_score = max(30, int(self.target_score * time_ratio + 5))
            warning_msg = f"🚨 绝对危机：需{int(required_hours)}小时，你只剩{int(available_hours)}小时！预计得分仅【{pred_score}分】。立刻放弃推导，只背核心公式！"
        elif time_ratio < 1.0:
            status = "时间紧迫"
            warning_msg = f"⚠️ 高危预警：任务量超出可用时间。建议抓大放小，战略性放弃冷门章节。"
        else:
            status = "安全充裕"
            warning_msg = f"✅ 时间充足：建议每天投入 {int(required_hours / self.days_left)} 小时，可深挖原理冲击高分。"

        return {
            "course_hardness": round(course_hardness, 1),
            "urgency_score": round(urgency_score, 1),
            "final_priority_weight": round(final_priority_weight, 1),
            "required_hours": round(required_hours, 1),
            "available_hours": round(available_hours, 1),
            "status": status,
            "warning_msg": warning_msg,
        }