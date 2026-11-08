"""老师重点解析与考点级硬校验（离线）。"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("TERMFINALE_HOME", "/tmp/tf_teacher_note_tests")

from core.quality.teacher_note import parse_teacher_note, topic_matches  # noqa: E402
from core.quality.constraints import (  # noqa: E402
    TaskConstraints, validate_output,
)

SOURCE = """【《有机化学》第 1 页】
命名规则与系统命名法。

【《有机化学》第 3 页】
下列有机基团的名称
-R -X -NO2 -SO3H -NH2 -CN -OH -COOH -CHO -OR
"""

MATH_SOURCE = """【《高数》第 1 页】
隐函数求导法。
【《高数》第 5 页】
例 3 参数方程求二阶导。
【《高数》第 8 页】
相关变化率。
"""


class ParseTest(unittest.TestCase):
    def test_only_whitelist(self):
        r = parse_teacher_note(
            "只考隐函数求导、高阶导数间接法、参数方程二阶导、变化率实际问题；其他不考")
        self.assertEqual(len(r.only_topics), 4)
        self.assertIn("隐函数求导", r.only_topics)
        self.assertIn("变化率实际问题", r.only_topics)
        self.assertNotIn("其他", "".join(r.ban_topics))

    def test_page_and_ban(self):
        r = parse_teacher_note("第 5 页例 3 必考，参数方程不考")
        self.assertEqual(r.page_refs, [5])
        self.assertTrue(any("参数方程" in t for t in r.ban_topics))

    def test_chemistry_token_list(self):
        r = parse_teacher_note(
            "不考 10 个基团命名：-R、-X、-NO2、-SO3H、-NH2、-CN、-OH、-COOH、-CHO、-OR；其余都考")
        for token in ("-R", "-X", "-NO2", "-SO3H", "-NH2", "-CN", "-OH", "-COOH", "-CHO", "-OR"):
            self.assertIn(token, r.literal_bans)

    def test_ambiguous_group_resolved_from_source(self):
        r = parse_teacher_note("命题那几个基团不考", SOURCE)
        self.assertGreaterEqual(len(r.literal_bans), 8)
        self.assertFalse(r.unresolved)
        self.assertTrue(any("自动解析" in n for n in r.notes))

    def test_matching(self):
        self.assertTrue(topic_matches("隐函数求导法", "隐函数求导"))
        self.assertTrue(topic_matches("相关变化率", "变化率实际问题"))
        self.assertFalse(topic_matches("积分中值定理", "隐函数求导"))


class TopicValidationTest(unittest.TestCase):
    def test_only_whitelist_hard(self):
        c = TaskConstraints(task="guide", only_topics=["隐函数求导"])
        md = "## 核心考点：导数\n\n### 1.1 积分中值定理\n\n正文（P.1）。"
        report = validate_output(md, c, source_text=MATH_SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("只考" in i for i in report.issues), report.issues)

    def test_body_mention_not_hard(self):
        c = TaskConstraints(task="guide", only_topics=["隐函数求导"])
        md = ("## 核心考点：导数\n\n### 1.1 隐函数求导\n\n"
              "这里顺带提到极限的思想，但只讲隐函数求导（P.1）。")
        report = validate_output(md, c, source_text=MATH_SOURCE, stage="final")
        self.assertTrue(report.ok, report.issues)

    def test_ban_topic_hard(self):
        c = TaskConstraints(task="guide", ban_topics=["参数方程"])
        md = "## 核心考点：导数\n\n### 1.1 参数方程求导\n\n正文（P.5）。"
        report = validate_output(md, c, source_text=MATH_SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("不考" in i for i in report.issues))

    def test_must_topic_missing_hard(self):
        c = TaskConstraints(task="guide", must_topics=["隐函数求导"])
        md = "## 核心考点：导数\n\n### 1.1 高阶导数\n\n正文（P.1）。"
        report = validate_output(md, c, source_text=MATH_SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("必考" in i for i in report.issues))

    def test_required_page_missing_hard(self):
        c = TaskConstraints(task="guide", required_pages=[5])
        md = "## 核心考点：导数\n\n### 1.1 隐函数求导\n\n正文（P.1）。"
        report = validate_output(md, c, source_text=MATH_SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("点名页码" in i for i in report.issues))

    def test_required_page_ok(self):
        c = TaskConstraints(task="guide", required_pages=[5])
        md = "## 核心考点：导数\n\n### 1.1 隐函数求导\n\n正文（P.5）。"
        report = validate_output(md, c, source_text=MATH_SOURCE, stage="final")
        self.assertTrue(report.ok, report.issues)

    def test_literal_token_hard(self):
        c = TaskConstraints(task="extract", extract_type="points", literal_bans=["-OH"])
        md = "### 考点：醇的命名\n- **是什么**：-OH 的命名。\n- [出处：《有机化学》第3页]\n"
        report = validate_output(md, c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("禁用" in i for i in report.issues))

    def test_chinese_exclude_is_topic_level(self):
        c = TaskConstraints(task="guide", exclude_terms=["积分"])
        body_only = "## 核心考点：导数\n\n### 1.1 高阶导数\n\n顺带讲讲积分的做法（P.1）。"
        heading = "## 核心考点：导数\n\n### 1.1 积分中值定理\n\n正文（P.1）。"
        self.assertTrue(validate_output(body_only, c, source_text=MATH_SOURCE,
                                        stage="final").ok)
        self.assertFalse(validate_output(heading, c, source_text=MATH_SOURCE,
                                         stage="final").ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class WeakAndBareTest(unittest.TestCase):
    def test_bare_kao_and_weak(self):
        r = parse_teacher_note("老师说考极限，不考中值定理；我隐函数那块不会，需要多讲")
        self.assertIn("极限", r.must_topics)
        self.assertIn("隐函数", r.weak_topics)
        self.assertIn("中值定理", r.ban_topics)
        self.assertNotIn("隐函数", r.ban_topics)

    def test_weak_prompt_and_hard_coverage(self):
        from core.quality.constraints import render_prompt
        c = TaskConstraints(task="guide", weak_topics=["隐函数"])
        self.assertIn("学生薄弱点", render_prompt(c))
        missing = validate_output("## 核心考点：导数\n\n正文（P.1）。", c,
                                  source_text=MATH_SOURCE, stage="final")
        self.assertFalse(missing.ok)
        self.assertTrue(any("学生薄弱点" in i for i in missing.issues), missing.issues)
        ok = validate_output("## 核心考点：导数\n\n### 隐函数\n\n从零讲起（P.1）。", c,
                             source_text=MATH_SOURCE, stage="final")
        self.assertTrue(ok.ok, ok.issues)
