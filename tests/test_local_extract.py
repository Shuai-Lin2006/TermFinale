"""Local candidate extraction must be page-grounded and never invent."""
from __future__ import annotations

import unittest

from tfv2.product import local_extract


class LocalExtractTests(unittest.TestCase):
    def test_points_cover_page_with_source_quote(self):
        text = {1: "第一章 导数\n导数的定义：函数在某点的瞬时变化率。\n定理 1 可导必连续。"}
        items = local_extract.extract_points(text, [1])
        self.assertGreaterEqual(len(items), 1)
        for item in items:
            self.assertEqual(item["page"], 1)
            self.assertTrue(item["quote"])
            self.assertIn(item["quote"][:8], text[1])

    def test_section_objectives_are_merged(self):
        text = {1: "作业 习题2.2\n第2.2节 求导的基本法则(2)\n• 高阶导数\n• 隐函数求导法\n• 由参数方程确定的函数求导法则"}
        items = local_extract.extract_points(text, [1])
        self.assertTrue(any("高阶导数" in x["point"] for x in items))

    def test_numbered_section_heading(self):
        text = {1: "2.函数的和、差、积、商的求导法则\n3、反函数的导数\n4、复合函数的求导法则"}
        items = local_extract.extract_points(text, [1])
        self.assertTrue(any("反函数" in x["point"] for x in items))

    def test_nouns_need_definition(self):
        text = {1: "导数：函数在某点的瞬时变化率。\n这是一个没有定义的句子。"}
        nouns = local_extract.extract_nouns(text, [1])
        self.assertEqual(nouns[0]["term"], "导数")
        self.assertIn("瞬时变化率", nouns[0]["definition"])

    def test_question_with_four_options(self):
        text = {1: "1. 神经传导的临床情境分析是什么？\nA. 选项一\nB. 选项二\nC. 选项三\nD. 选项四"}
        items = local_extract.extract_questions(text, [1])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["qtype"], "choice")
        self.assertEqual(len(items[0]["options"]), 4)
        self.assertEqual(items[0]["source_no"], "1")
        self.assertIsNone(items[0]["answer"])

    def test_parenthesized_question_numbers(self):
        text = {1: "(1) 求极限并说明理由。\n【答案】A\n(2) 求导数并写出步骤。"}
        items = local_extract.extract_questions(text, [1])
        self.assertEqual([x["source_no"] for x in items], ["1", "2"])

    def test_question_without_options_is_short_answer(self):
        text = {1: "2. 请解释动作电位传播的机制。"}
        items = local_extract.extract_questions(text, [1])
        self.assertEqual(items[0]["qtype"], "short_answer")
        self.assertEqual(items[0]["answer_text"], "原卷未给答案")

    def test_blank_page_does_not_fabricate(self):
        self.assertEqual(local_extract.extract_points({1: ""}, [1]), [])
        self.assertEqual(local_extract.extract_nouns({1: ""}, [1]), [])


if __name__ == "__main__":
    unittest.main()
