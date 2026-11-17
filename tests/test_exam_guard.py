"""试卷误杀防护：教材里出现“期中/姓名”不算试卷。"""
from __future__ import annotations

import unittest

from tfv2.product.generate import looks_like_exam

BOOK_PREFACE = (
    "前言之二\n较之二零年六月的版本，讲义增加了数学分析第三学期的讲义，主要研究 Schwartz 的分布理论。"
    "这套讲义在期中考试之前会讲完，具体安排见课程网站。" * 2
)
BOOK_HOMEWORK = (
    "作业：隐函数与反函数定理，隐函数定理在多项式和矩阵上的一个重要应用。"
    "清华大学19-20 春季学期，数学分析二，作业3。请用A4大小的纸张正反面书写，并注明自己的姓名、年级。" * 2
)
EXAM_TEXT = (
    "A卷 重庆大学《高等数学》期中考试试卷\n"
    "考试方式:闭卷 考试时间:120分钟\n"
    "题号 一 二 三 四 五 总分\n"
    "得分\n姓名 学号 班级\n"
    "一、单项选择题(每小题3分,共18分)" * 2
)


class ExamGuardTests(unittest.TestCase):
    def test_book_preface_not_exam(self) -> None:
        self.assertFalse(looks_like_exam(BOOK_PREFACE))

    def test_book_homework_not_exam(self) -> None:
        self.assertFalse(looks_like_exam(BOOK_HOMEWORK))

    def test_real_exam_detected(self) -> None:
        self.assertTrue(looks_like_exam(EXAM_TEXT))

    def test_short_text_not_exam(self) -> None:
        self.assertFalse(looks_like_exam("题号 得分"))
