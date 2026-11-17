
"""Round 1: structured user exclusions (20 phrasing samples + filters)."""
from __future__ import annotations

import unittest

from tfv2.domain.lecture import BlockKind, LectureBlock, SourceRef
from tfv2.product import exclusions


CASES = [
    ("第三章不考", [("section", "第3章")]),
    ("第3章不考", [("section", "第3章")]),
    ("第20页不用看", [("page", "20")]),
    ("第 12 页跳过", [("page", "12")]),
    ("积分中值定理不考", [("topic", "积分中值定理")]),
    ("老师说不考泰勒展开", [("topic", "泰勒展开")]),
    ("别考生僻词", [("topic", "生僻词")]),
    ("实验部分跳过", [("topic", "实验")]),
    ("计算题不考", [("question_type", "calculation")]),
    ("只考选择题", [("question_type_allow", "choice")]),
    ("简答题不考", [("question_type", "short_answer")]),
    ("不考第4章", [("section", "第4章")]),
    ("第5章和第6章不考", [("section", "第5章"), ("section", "第6章")]),
    ("除了积分中值定理都考", [("topic", "积分中值定理")]),
    ("我们老师强调不定积分不考", [("topic", "不定积分")]),
    ("第30页不用复习", [("page", "30")]),
    ("判断题不考", [("question_type", "judgment")]),
    ("只考到第5章", [("section_limit", "5")]),
]


class ParseTests(unittest.TestCase):
    def test_eighteen_scoped_phrases(self):
        for text, expected in CASES:
            got = exclusions.parse_exclusions(text)
            pairs = [(s["scope"], s["value"]) for s in got["specs"]]
            self.assertEqual(pairs, expected, text)

    def test_ambiguous_phrases_are_not_deleted(self):
        for text in ("这个考点不考", "不考太多"):
            got = exclusions.parse_exclusions(text)
            self.assertEqual(got["specs"], [], text)
            self.assertTrue(got["ambiguous"], text)


class MatchTests(unittest.TestCase):
    def setUp(self):
        self.page_text = {
            1: "积分中值定理：若函数连续，则存在一点使积分等于函数值乘区间长度。",
            2: "定积分的计算：牛顿-莱布尼茨公式。",
            3: "泰勒展开：用多项式逼近函数。",
            4: "实验：测量导体的伏安特性。",
        }
        self.sections = [
            {"id": "s1", "title": "第一章 积分", "pages": [1, 2]},
            {"id": "s2", "title": "第二章 泰勒", "pages": [3]},
            {"id": "s3", "title": "第三章 实验", "pages": [4]},
        ]
        self.index = exclusions.build_index(self.page_text, self.sections)

    def test_topic_matches_only_target_page(self):
        specs = exclusions.parse_exclusions("积分中值定理不考")["specs"]
        matched = exclusions.match_specs(specs, self.index)
        self.assertEqual(matched[0]["matched"]["pages"], [1])
        self.assertNotIn(2, matched[0]["matched"]["pages"])

    def test_broad_topic_needs_confirmation(self):
        specs = exclusions.parse_exclusions("积分不考")["specs"]
        matched = exclusions.match_specs(specs, self.index)
        self.assertTrue(matched[0]["needs_confirm"])

    def test_section_and_page(self):
        specs = exclusions.parse_exclusions("第3章不考")["specs"]
        matched = exclusions.match_specs(specs, self.index)
        self.assertEqual(matched[0]["matched"]["pages"], [4])

    def test_section_limit_excludes_later_chapters(self):
        page_text = {1: "第一章 基础", 2: "第二章 进阶", 3: "第六章 超纲"}
        sections = [
            {"id": "s1", "title": "第一章 基础", "pages": [1]},
            {"id": "s2", "title": "第二章 进阶", "pages": [2]},
            {"id": "s6", "title": "第六章 超纲", "pages": [3]},
        ]
        index = exclusions.build_index(page_text, sections)
        specs = exclusions.parse_exclusions("只考到第5章")["specs"]
        matched = exclusions.match_specs(specs, index)
        self.assertEqual(matched[0]["matched"]["pages"], [3])
        self.assertFalse(matched[0]["needs_confirm"])

    def test_alias_expansion(self):
        page_text = {1: "泰勒展开用于近似函数。"}
        index = exclusions.build_index(page_text, [])
        specs = exclusions.parse_exclusions("泰勒公式不考")["specs"]
        matched = exclusions.match_specs(specs, index)
        self.assertEqual(matched[0]["matched"]["pages"], [1])

    def test_preview_lists_pages_and_pending(self):
        result = exclusions.preview_exclusions(
            "积分中值定理不考\n这个考点不考",
            {1: "积分中值定理", 2: "定积分"},
            [{"id": "s1", "title": "第一章 积分", "pages": [1, 2]}],
        )
        self.assertEqual(result["preview"]["pages"], [1])
        self.assertTrue(result["requires_confirmation"])
        self.assertTrue(result["ambiguous"])

    def test_prompt_contains_exclusion(self):
        specs = exclusions.parse_exclusions("积分中值定理不考")["specs"]
        prompt = exclusions.exclusion_prompt(specs)
        self.assertIn("积分中值定理", prompt)
        self.assertIn("不要主动展开", prompt)
        self.assertIn("顺带提到", prompt)


class FilterTests(unittest.TestCase):
    def test_blocks_do_not_delete_related_topic(self):
        specs = exclusions.parse_exclusions("积分中值定理不考")["specs"]
        def block(bid, text, page):
            return LectureBlock(id=bid, kind=BlockKind.PARAGRAPH, text=text,
                                source_refs=[SourceRef(material="m", page_start=page, page_end=page)])
        blocks = [
            block("a", "积分中值定理的证明。", 1),
            block("b", "定积分的计算。", 2),
        ]
        kept, removed = exclusions.filter_blocks(blocks, specs)
        self.assertEqual([b.id for b in kept], ["b"])
        self.assertEqual(removed, 1)

    def test_extract_items(self):
        specs = exclusions.parse_exclusions("泰勒展开不考")["specs"]
        items = [
            {"point": "泰勒展开", "detail": "用多项式逼近"},
            {"point": "定积分", "detail": "牛顿-莱布尼茨"},
        ]
        kept, removed = exclusions.filter_items(items, specs, "extract_points")
        self.assertEqual([x["point"] for x in kept], ["定积分"])
        self.assertEqual(removed, 1)

    def test_exam_parser_rejects_excluded_question(self):
        from tfv2.product.exam import _parse_question
        specs = exclusions.parse_exclusions("积分中值定理不考")["specs"]
        raw = {
            "qtype": "choice", "stem": "关于积分中值定理，下列说法正确的是",
            "options": ["A", "B", "C", "D"], "answer": 0,
            "analysis": "积分中值定理的内容", "source_page": 1,
            "source_no": "1",
        }
        q, issue = _parse_question(raw, {1}, {1: "积分中值定理"}, "mock", "数学", excluded_specs=specs)
        self.assertIsNone(q)
        self.assertIn("排除", issue)

    def test_questions(self):
        specs = exclusions.parse_exclusions("计算题不考")["specs"]
        qs = [
            {"qtype": "calculation", "stem": "计算积分", "options": [], "analysis": "..."},
            {"qtype": "choice", "stem": "积分中值定理", "options": ["A", "B", "C", "D"], "analysis": "..."},
        ]
        kept, removed = exclusions.filter_questions(qs, specs, "exam")
        # question_type does not text-match; both remain. It is enforced by blueprint/type allow.
        self.assertEqual(len(kept), 2)
        self.assertEqual(removed, 0)


if __name__ == "__main__":
    unittest.main()
