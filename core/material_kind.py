"""资料适用性判断：考试资料 / 课堂讲义 / 习题 / 不确定。"""
from __future__ import annotations

EXAM = ["期末", "考试", "考点", "题型", "分值", "真题", "复习", "押题", "试卷", "大纲", "重点", "样卷", "答案"]
LECTURE = ["课堂", "lecture", "discussion", "group work", "activity", "learning objective", "agenda",
           "homework", "presentation", "unit", "lesson", "课堂活动", "讨论", "小组", "作业", "教学目标"]
EXERCISE = ["习题", "练习", "作业题", "exercise", "problem set", "questions", "答案"]


def classify_text(text: str, filename: str = "") -> dict:
    name_l = (filename or "").lower()
    if any(k in name_l for k in ("讲义", "教材", "课本", "教程", "系统课", "lecture", "textbook")):
        return {"kind": "lecture", "confidence": 0.85, "reasons": ["文件名表明是讲义/教材"]}
    if any(k in name_l for k in ("试卷", "真题", "exam paper", "期末试卷")):
        return {"kind": "exam", "confidence": 0.88, "reasons": ["文件名表明是试卷/真题"]}
    t = (filename + "\n" + (text or "")[:6000]).lower()
    exam = sum(1 for k in EXAM if k.lower() in t)
    lecture = sum(1 for k in LECTURE if k.lower() in t)
    exercise = sum(1 for k in EXERCISE if k.lower() in t)
    if exercise >= 2 and exam >= 1:
        kind, conf = "exam", 0.78
    elif exam >= 3 and exam > lecture:
        kind, conf = "exam", min(0.92, 0.55 + exam * 0.06)
    elif lecture >= 2 and lecture >= exam:
        kind, conf = "lecture", min(0.9, 0.55 + lecture * 0.06)
    elif exam >= 1:
        kind, conf = "exam", 0.58
    else:
        kind, conf = "unknown", 0.5
    reasons = []
    if exam: reasons.append(f"考试相关词 {exam} 个")
    if lecture: reasons.append(f"课堂/活动词 {lecture} 个")
    if exercise: reasons.append(f"习题词 {exercise} 个")
    return {"kind": kind, "confidence": round(conf, 2), "reasons": reasons}
