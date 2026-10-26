class CourseInfo:
    #1.在类的顶部定义字典
    SCHOOl_WEIGHT_MAP = {
        "上9":1.6,
        "中9":1.5,
        "下9":1.4,
        "上2":1.3,
        "中2":1.2,
        "下2":1.1,
        "普通一本":1.0,
        "普通二本":0.9,
        "专科":0.8,

    }
    def __init__(self, name: str, school: str, credits: float, days: int, target: int, user_difficulty: int, is_major: bool):
        self.course_name = name
        self.school_level= school  #用户输入的学校层级，比如“中9”
        self.credits = credits
        self.days_left = days
        self.target_score = target
        self.user_difficulty = user_difficulty
        self.is_major = is_major

    def calculate_weight(self):
            # 简单算法:学分 * 目标分数比例
            base_weight = self.credits * (self.target_score / 100.0)

            multiplier = self.SCHOOl_WEIGHT_MAP.get(self.school_level, 1.0)

            difficulty_bonus = 1.0 + (self.user_difficulty - 1) * 0.1

            major_bonus = 1.2 if self.is_major else 1.0

            if self.days_left <= 7:
                urgency_bonus = 1.5
            elif self.days_left <= 14:
                urgency_bonus = 1.2
            else:
                urgency_bonus = 1.0

            final_weight = base_weight * multiplier * difficulty_bonus * major_bonus *urgency_bonus

            return round(final_weight, 2)


