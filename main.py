from models.user_profile import CourseInfo

#测试
course = CourseInfo(name="高数",school="中9",credits=4.0,days=7,target=90,user_difficulty=5,is_major=True)
print(f"课程名称:{course.course_name}")
print(f"学校层级:{course.school_leval}")
print(f"学分:{course.credits}")
print(f"剩余天数:{course.days_left}")
print(f"目标分数{course.target_score}")
print(f"自评难度:{course.user_difficulty}")
print(f"是否专业课:{course.is_major}")
print(f"算出来的权重:{course.calculate_weight()}")