"""任务级约束与生成后硬校验的离线测试（不调用任何网络接口）。"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("TERMFINALE_HOME", tempfile.mkdtemp(prefix="tf_constraints_"))
os.environ.setdefault("TERMFINALE_DISABLE_VISION", "1")

from core.quality.constraints import (  # noqa: E402
    TaskConstraints,
    validate_output,
    scope_pages,
    source_pages,
    cited_pages,
    unsupported_terms,
    render_prompt,
)
from core.quality.gate import ConstraintViolation, generate_until_valid  # noqa: E402
from core.generate.exam_builder import blueprint_from_sections, validate_paper  # noqa: E402


SOURCE = """【《资料A》第 1 页】
第2.2节 高阶导数与隐函数求导
[[[IMAGE: a1.png | 图注: 第 1 页配图]]]

【《资料A》第 2 页】
参数方程确定的函数求导法则、相关变化率
"""


def _exam_paper(title: str = "期末试卷") -> str:
    selection = "\n".join(
        f"{i}. 关于高阶导数的说法，正确的是（ ）\nA. 甲\nB. 乙\nC. 丙\nD. 丁\n【考点：高阶导数】\n"
        for i in range(1, 7))
    fill = "\n".join(f"{i}. 高阶导数 ____。【考点：高阶导数】\n" for i in range(1, 4))
    calc = "\n".join(f"{i}. 求 $y=x^2$ 的二阶导数。【考点：高阶导数】\n" for i in range(1, 3))
    answers = "\n".join(f"{i}. A" for i in range(1, 12))
    return (f"# {title}\n**满分：100 分**\n\n"
            f"## 单项选择题（6 题，每题 5 分，共 30 分）\n{selection}\n"
            f"## 填空题（3 题，每题 10 分，共 30 分）\n{fill}\n"
            f"## 计算题（2 题，每题 20 分，共 40 分）\n{calc}\n"
            f"# 答案与解析\n{answers}\n")


class ConstraintOptionsTest(unittest.TestCase):
    def test_nested_options(self):
        c = TaskConstraints.from_options("extract", {
            "extract_type": "questions", "with_answer": False,
            "constraints": {"page_start": 9, "page_end": 3,
                            "exclude_terms": "极限，积分 极限", "strict": False},
        })
        self.assertEqual((c.page_start, c.page_end), (3, 9))  # 自动交换
        self.assertEqual(c.exclude_terms, ["极限", "积分"])   # 去重
        self.assertEqual(c.answer_mode, "forbidden")
        self.assertFalse(c.strict)

    def test_default_scope_off(self):
        c = TaskConstraints.from_options("guide", {})
        self.assertFalse(c.has_scope)
        self.assertEqual(c.answer_mode, "optional")


class PageHelpersTest(unittest.TestCase):
    def test_source_and_cited_pages(self):
        self.assertEqual(source_pages(SOURCE), {1, 2})
        text = "见第1页与（P.2），图注 [[[IMAGE: x | 图注: 第 7 页配图]]]"
        self.assertEqual(cited_pages(text), {1, 2})  # 图片标签不算页码引用

    def test_scope_pages(self):
        pages = ["【《a》第 1 页】\nx", "【《a》第 2 页】\ny", "【《a》第 3 页】\nz"]
        self.assertEqual(scope_pages(pages, TaskConstraints(page_start=2, page_end=3)),
                         pages[1:])
        self.assertEqual(scope_pages(pages, TaskConstraints(page_start=9)), [])


class GuideValidationTest(unittest.TestCase):
    def setUp(self):
        self.c = TaskConstraints(task="guide")

    def test_ok(self):
        md = "## 核心考点：高阶导数\n\n正文见（P.1）。"
        report = validate_output(md, self.c, source_text=SOURCE, allowed_pages={1})
        self.assertTrue(report.ok, report.issues)

    def test_exclude_term_is_hard(self):
        c = TaskConstraints(task="guide", exclude_terms=["积分"])
        md = "## 核心考点：高阶导数\n\n### 1.1 积分中值定理\n\n正文。"
        report = validate_output(md, c, source_text=SOURCE)
        self.assertFalse(report.ok)
        self.assertTrue(any("不考" in i for i in report.issues), report.issues)

    def test_invented_page_is_hard(self):
        md = "## 核心考点：高阶导数\n\n出处（P.9）。"
        report = validate_output(md, self.c, source_text=SOURCE, allowed_pages={1, 2})
        self.assertFalse(report.ok)
        self.assertTrue(any("页码" in i for i in report.issues))

    def test_ungrounded_topic_is_warning(self):
        md = "## 核心考点：高阶导数\n\n### 1.1 积分中值定理\n\n正文（P.1）。"
        report = validate_output(md, self.c, source_text=SOURCE, allowed_pages={1, 2})
        self.assertTrue(report.ok, report.issues)
        self.assertTrue(any("资料中没有" in w for w in report.warnings))

    def test_grounding(self):
        self.assertEqual(unsupported_terms(["极限", "定积分"], SOURCE), ["极限", "定积分"])
        self.assertEqual(unsupported_terms(["高阶导数", "参数方程"], SOURCE), [])


class ExtractValidationTest(unittest.TestCase):
    def test_points_need_citations(self):
        c = TaskConstraints(task="extract", extract_type="points")
        md = "### 考点：高阶导数\n- **是什么**：定义。\n"
        report = validate_output(md, c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("出处" in i for i in report.issues))

    def test_citation_out_of_range(self):
        c = TaskConstraints(task="extract", extract_type="points")
        md = "### 考点：高阶导数\n- **是什么**：定义。\n- [出处：《资料A》第8页]\n"
        report = validate_output(md, c, source_text=SOURCE, allowed_pages={1, 2}, stage="final")
        self.assertFalse(report.ok)

    def test_missing_page_note_is_hard(self):
        c = TaskConstraints(task="extract", extract_type="points")
        md = "### 考点：高阶导数\n- **是什么**：定义。\n- [出处：资料未标注页码]\n"
        report = validate_output(md, c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)

    def test_questions_forbidden_answers(self):
        c = TaskConstraints(task="extract", extract_type="questions", answer_mode="forbidden")
        md = "1. 求 $y=x^2$ 的导数\n【答案】$2x$\n"
        report = validate_output(md, c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("答案" in i for i in report.issues))

    def test_questions_required_answers(self):
        c = TaskConstraints(task="extract", extract_type="questions", answer_mode="required")
        md = "1. 求 $y=x^2$ 的导数\n第二题\n"
        report = validate_output(md, c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)

    def test_questions_no_questions(self):
        c = TaskConstraints(task="extract", extract_type="questions", answer_mode="required")
        source_q = "【《资料A》第 1 页】\n1. 求 $y=x^2$ 的导数\n2. 求高阶导数\n"
        md = "### 注释\n这段资料没有题目。\n"
        report = validate_output(md, c, source_text=source_q, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("没有识别到任何题目" in i for i in report.issues))

    def test_questions_empty_source_is_warning(self):
        c = TaskConstraints(task="extract", extract_type="questions", answer_mode="required")
        md = "【本段无题目】\n"
        report = validate_output(md, c, source_text="【《资料A》第 1 页】\n纯概念，无题。",
                                 stage="final")
        self.assertTrue(report.ok, report.issues)
        self.assertTrue(any("没有识别到题目" in w for w in report.warnings))


class ExamValidationTest(unittest.TestCase):
    def setUp(self):
        self.c = TaskConstraints(task="exam", answer_mode="required", sections=[
            {"name": "单项选择题", "count": 6, "points": 5},
            {"name": "填空题", "count": 3, "points": 10},
            {"name": "计算题", "count": 2, "points": 20},
        ])
        self.paper = _exam_paper()

    def test_ok(self):
        report = validate_output(self.paper, self.c, source_text=SOURCE, stage="final")
        self.assertTrue(report.ok, report.issues)
        self.assertEqual(report.metrics.get("score_total"), 100.0)

    def test_wrong_count_fails(self):
        broken = self.paper.replace("6. 关于高阶导数", "附加题：关于高阶导数")
        report = validate_output(broken, self.c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)

    def test_missing_answers_fails(self):
        body = self.paper.split("# 答案与解析")[0]
        report = validate_output(body, self.c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("答案与解析" in i for i in report.issues))

    def test_no_source_page_citations(self):
        paper = self.paper.replace("关于高阶导数的说法", "参考原资料第3页的说法")
        report = validate_output(paper, self.c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("原资料页码" in i for i in report.issues))

    def test_extra_type_fails(self):
        paper = self.paper.replace("## 填空题", "## 判断题\n1. 对。\n\n## 填空题")
        report = validate_output(paper, self.c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("未允许的题型" in i for i in report.issues))


class GateTest(unittest.TestCase):
    def test_retry_then_pass(self):
        calls = {"n": 0}

        def gen(feedback: str) -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                return "### 考点：极限\n- 定义\n- [出处：《资料A》第1页]\n"
            self.assertIn("未通过", feedback)
            return "### 考点：高阶导数\n- 定义\n- [出处：《资料A》第1页]\n"

        c = TaskConstraints(task="extract", extract_type="points", exclude_terms=["极限"])
        md, report = generate_until_valid(
            gen, c, source_text=SOURCE, allowed_pages={1, 2}, stage="final")
        self.assertTrue(report.ok, report.issues)
        self.assertEqual(report.metrics["attempts"], 2)
        self.assertEqual(calls["n"], 2)

    def test_exhausted_retries_raise(self):
        c = TaskConstraints(task="extract", extract_type="points",
                            exclude_terms=["极限"], max_retries=2)
        with self.assertRaises(ConstraintViolation):
            generate_until_valid(
                lambda _fb: "### 考点：极限\n- 定义\n- [出处：《资料A》第1页]\n",
                c, source_text=SOURCE, stage="final")
        self.assertEqual(c.max_retries, 2)  # 1 次初稿 + 2 次重试

    def test_non_strict_keeps_result(self):
        c = TaskConstraints(task="extract", extract_type="points",
                            exclude_terms=["极限"], strict=False, max_retries=1)
        md, report = generate_until_valid(
            lambda _fb: "### 考点：极限\n- 定义\n- [出处：《资料A》第1页]\n",
            c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(md)


class ExamGenerationTest(unittest.TestCase):
    """生成与校验必须共用同一份 structures，且约束真的进了提示词。"""

    def _fake_llm(self, prompts: list[str]):
        def _call(sys_prompt, user_content, temp=0.1, min_budget=0):
            prompts.append(sys_prompt)
            if "答案撰写人" in sys_prompt or "答案与解析" in sys_prompt:
                return "# 答案与解析\n" + "\n".join(f"{i}. A" for i in range(1, 12))
            import re as _re
            m = _re.search(r"本次只出「(.+?)」这一种题型：(\d+) 题，每题 ([\d.]+) 分", sys_prompt)
            if not m:
                return ""
            title, count, points = m.group(1), int(m.group(2)), float(m.group(3))
            qs = "\n".join(
                f"{i}. 关于高阶导数的题目（{title}）。【考点：高阶导数】"
                for i in range(1, count + 1))
            return (f"## {title}（{count} 题，每题 {points:g} 分，共 {count * points:g} 分）\n"
                    + qs)
        return _call

    def test_blueprint_drives_generation_and_validation(self):
        from core.exam_engine import generate_exam_paper

        prompts: list[str] = []
        blueprint = blueprint_from_sections([
            {"name": "单项选择题", "count": 6, "points": 5},
            {"name": "填空题", "count": 3, "points": 10},
            {"name": "计算题", "count": 2, "points": 20},
        ])
        with patch("core.exam_engine.call_ai_with_retry", self._fake_llm(prompts)), \
             patch("core.exam_engine._qwen_fallback", lambda *a, **k: ""):
            md = generate_exam_paper(SOURCE, "mock", 1, 3, blueprint=blueprint,
                                     course_name="测试课")
        self.assertIn("# 测试课 期末试卷", md)
        self.assertIn("**满分：100 分**", md)
        c = TaskConstraints(task="exam", answer_mode="required", sections=[
            {"name": "单项选择题", "count": 6, "points": 5},
            {"name": "填空题", "count": 3, "points": 10},
            {"name": "计算题", "count": 2, "points": 20},
        ])
        report = validate_output(md, c, source_text=SOURCE, stage="final")
        self.assertTrue(report.ok, report.issues)
        self.assertTrue(any("6 题" in p for p in prompts), prompts[:2])

    def test_diy_config_path_does_not_crash(self):
        from core.exam_engine import generate_exam_paper

        def _call(sys_prompt, user_content, temp=0.1, min_budget=0):
            if "答案" in sys_prompt:
                return "# 答案与解析\n1. A\n2. B\n3. C\n"
            return "# 期末试卷\n**满分：100 分**\n\n## 一、选择题\n1. 题\n"

        with patch("core.exam_engine.call_ai_with_retry", _call), \
             patch("core.exam_engine._qwen_fallback", lambda *a, **k: ""):
            md = generate_exam_paper(SOURCE, "mock", 1, 3, diy_config="一、选择题 10 题 × 10 分")
        self.assertIn("答案与解析", md)

    def test_answer_forbidden(self):
        from core.exam_engine import generate_exam_paper

        prompts: list[str] = []
        blueprint = blueprint_from_sections([{"name": "单项选择题", "count": 2, "points": 50}])
        with patch("core.exam_engine.call_ai_with_retry", self._fake_llm(prompts)), \
             patch("core.exam_engine._qwen_fallback", lambda *a, **k: ""):
            md = generate_exam_paper(SOURCE, "mock", 1, 3, blueprint=blueprint,
                                     with_answers=False)
        self.assertNotIn("# 答案与解析", md)


class StrictPaperTest(unittest.TestCase):
    def test_strict_counts_marks_error(self):
        paper = _exam_paper()
        blueprint = blueprint_from_sections([
            {"name": "单项选择题", "count": 7, "points": 5},
            {"name": "填空题", "count": 3, "points": 10},
            {"name": "计算题", "count": 2, "points": 20},
        ])
        loose = validate_paper(paper, blueprint, strict_counts=False)
        strict = validate_paper(paper, blueprint, strict_counts=True)
        self.assertFalse(loose.ok)  # 分值合计也不对
        self.assertFalse(strict.ok)
        self.assertTrue(any("题数" in i and i.startswith("[error]") for i in strict.issues))
        self.assertTrue(any(i.startswith("[warn]") for i in loose.issues))

    def test_prompt_contains_task_constraints(self):
        c = TaskConstraints(task="exam", answer_mode="forbidden",
                            exclude_terms=["积分"], page_start=1, page_end=2,
                            sections=[{"name": "计算题", "count": 2, "points": 50}])
        prompt = render_prompt(c)
        self.assertIn("只有题目", prompt.replace("只输出题目", "只有题目"))
        self.assertIn("积分", prompt)
        self.assertIn("第 1–2 页", prompt)
        self.assertIn("计算题", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class BracketedFilenameTest(unittest.TestCase):
    """文件名含【】时，页码校验不能整体失明。"""

    def test_source_pages_with_brackets(self):
        text = "【《有机化学【蜂考系统课】.pdf》第 5 页】\n内容"
        self.assertEqual(source_pages(text), {5})

    def test_scope_with_brackets(self):
        pages = ["【《有机化学【蜂考系统课】.pdf》第 5 页】\nA",
                 "【《有机化学【蜂考系统课】.pdf》第 6 页】\nB"]
        self.assertEqual(scope_pages(pages, TaskConstraints(page_start=6, page_end=6)),
                         [pages[1]])


class ExamToleranceTest(unittest.TestCase):
    def _c(self, mode="required"):
        return TaskConstraints(task="exam", answer_mode=mode, sections=[
            {"name": "单项选择题", "count": 6, "points": 5},
            {"name": "填空题", "count": 3, "points": 10},
            {"name": "计算题", "count": 2, "points": 20},
        ])

    def test_answer_forbidden_passes(self):
        body = _exam_paper().split("# 答案与解析")[0]
        report = validate_output(body, self._c("forbidden"), source_text=SOURCE, stage="final")
        self.assertTrue(report.ok, report.issues)

    def test_answer_heading_with_suffix(self):
        paper = _exam_paper().replace("# 答案与解析", "# 答案与解析（详解）")
        report = validate_output(paper, self._c("required"), source_text=SOURCE, stage="final")
        self.assertTrue(report.ok, report.issues)

    def test_extra_heading_only_warns(self):
        paper = _exam_paper().replace(
            "## 单项选择题（6 题，每题 5 分，共 30 分）",
            "## 考试说明\n\n本卷共 100 分。\n\n## 单项选择题（6 题，每题 5 分，共 30 分）")
        report = validate_output(paper, self._c("required"), source_text=SOURCE, stage="final")
        self.assertTrue(report.ok, report.issues)
        self.assertTrue(any("额外标题" in w for w in report.warnings), report.warnings)


class AnswerConsistencyTest(unittest.TestCase):
    def test_low_answer_coverage_fails(self):
        paper = _exam_paper()
        body = paper.split("# 答案与解析")[0]
        broken = body + "# 答案与解析\n1. A\n"
        c = TaskConstraints(task="exam", answer_mode="required", sections=[
            {"name": "单项选择题", "count": 6, "points": 5},
            {"name": "填空题", "count": 3, "points": 10},
            {"name": "计算题", "count": 2, "points": 20},
        ])
        report = validate_output(broken, c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("答案不完整" in i or "答案不足" in i for i in report.issues), report.issues)

    def test_empty_answer_line_fails(self):
        paper = _exam_paper().replace("# 答案与解析\n1. A", "# 答案与解析\n1.\n")
        c = TaskConstraints(task="exam", answer_mode="required", sections=[
            {"name": "单项选择题", "count": 6, "points": 5},
            {"name": "填空题", "count": 3, "points": 10},
            {"name": "计算题", "count": 2, "points": 20},
        ])
        report = validate_output(paper, c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("为空" in i for i in report.issues), report.issues)


class MultiAnswerPaperTest(unittest.TestCase):
    def test_second_answer_section_fails(self):
        paper = _exam_paper() + "\n# 答案与解析\n1. A\n## 填空题（2 题，每题 10 分）\n1. 新题\n"
        c = TaskConstraints(task="exam", answer_mode="required", sections=[
            {"name": "单项选择题", "count": 6, "points": 5},
            {"name": "填空题", "count": 3, "points": 10},
            {"name": "计算题", "count": 2, "points": 20},
        ])
        report = validate_output(paper, c, source_text=SOURCE, stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("答案分区" in i for i in report.issues), report.issues)


class EveryAnswerRequiredTest(unittest.TestCase):
    PAPER = """# 期末试卷
## 单项选择题
1. 第一题
A. 1 B. 2
2. 第二题
A. 1 B. 2
## 填空题
1. 第三题
2. 第四题
# 答案与解析
## 单项选择题
1. A
2. B
"""
    def _c(self):
        return TaskConstraints(task="exam", answer_mode="required")

    def test_missing_whole_section_fails(self):
        report = validate_output(self.PAPER, self._c(), source_text="", stage="final")
        self.assertFalse(report.ok)
        self.assertTrue(any("缺少大题" in i or "答案不完整" in i for i in report.issues), report.issues)

    def test_all_sections_answered_passes(self):
        paper = self.PAPER + "## 填空题\n1. 第一空\n2. 第二空\n"
        report = validate_output(paper, self._c(), source_text="", stage="final")
        self.assertTrue(report.ok, report.issues)


class ChoiceAnswerLetterTest(unittest.TestCase):
    def _paper(self, answer):
        return ("# 试卷\n## 单项选择题\n"
                "1. 题干\nA. 一\nB. 二\nC. 三\nD. 四\n"
                "# 答案与解析\n## 单项选择题\n1. " + answer + "\n")

    def test_valid_letter_passes(self):
        c = TaskConstraints(task="exam", answer_mode="required")
        r = validate_output(self._paper("B"), c, source_text="", stage="final")
        self.assertTrue(r.ok, r.issues)

    def test_letter_not_in_options_fails(self):
        c = TaskConstraints(task="exam", answer_mode="required")
        r = validate_output(self._paper("E"), c, source_text="", stage="final")
        self.assertFalse(r.ok)
        self.assertTrue(any("不在选项" in i for i in r.issues), r.issues)

    def test_non_letter_answer_fails(self):
        c = TaskConstraints(task="exam", answer_mode="required")
        r = validate_output(self._paper("因为显然"), c, source_text="", stage="final")
        self.assertFalse(r.ok)
        self.assertTrue(any("不是选项字母" in i for i in r.issues), r.issues)
