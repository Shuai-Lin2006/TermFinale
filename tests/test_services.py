"""服务层集成测试：约束真的进入提示词、违规重试、严格模式判失败。

全部离线：生成函数被替换成假实现，不调用任何网络接口。
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HOME = tempfile.mkdtemp(prefix="tf_services_")
_OUT = tempfile.mkdtemp(prefix="tf_out_")
os.environ.setdefault("TERMFINALE_HOME", _HOME)
os.environ["TERMFINALE_OUTPUT_DIR"] = _OUT
os.environ["TERMFINALE_DISABLE_VISION"] = "1"

from core.database import Course, Material, get_db_session, init_db  # noqa: E402
from core.generate.outline import Chapter, Outline  # noqa: E402
from core.quality.constraints import TaskConstraints  # noqa: E402
from core.quality.gate import ConstraintViolation  # noqa: E402
from services import guide_service, review_service  # noqa: E402

COURSE = {
    "id": 9001, "name": "约束集成测试", "school": "一本", "major": "测试",
    "is_major": True, "credits": 3.0, "days_left": 7, "target_score": 80,
    "difficulty": 3, "foundation": 3, "materials": [],
}


def _ensure_course(course_id: int = 9001) -> None:
    init_db()
    db = get_db_session()
    try:
        if not db.query(Course).filter(Course.id == course_id).first():
            db.add(Course(id=course_id, name=COURSE["name"], major="测试",
                          school_level="一本", credits=3.0, days_left=7,
                          target_score=80, user_difficulty=3, self_difficulty=3,
                          foundation=3, is_major=True, persona="老师"))
            db.commit()
    finally:
        db.close()


def _make_pptx(pages: list[str]) -> str:
    from pptx import Presentation

    prs = Presentation()
    for text in pages:
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = text
    path = Path(tempfile.mkdtemp()) / "scope.pptx"
    prs.save(path)
    return str(path)


class ExtractServiceTest(unittest.TestCase):
    TEXT = ("【《约束资料》第 1 页】\n第一章 引论，只讲背景。\n\n"
            "【《约束资料》第 2 页】\n第二章 高阶导数与隐函数求导。\n\n"
            "【《约束资料》第 3 页】\n第三章 参数方程求导与相关变化率。\n")

    def setUp(self):
        _ensure_course()

    def test_scope_and_retry(self):
        calls: list[dict] = []

        def fake_extract(chunk, extract_type, with_answer, user_note="", constraint_block=""):
            calls.append({"chunk": chunk, "note": user_note, "block": constraint_block})
            if len(calls) == 1:
                return "### 考点：积分技巧\n- **是什么**：凑微分。\n- [出处：《约束资料》第2页]\n"
            page = "2" if "第 2 页" in chunk else "3"
            return f"### 考点：高阶导数{page}\n- **是什么**：求导。\n- [出处：《约束资料》第{page}页]\n"

        c = TaskConstraints(task="extract", extract_type="points", answer_mode="optional",
                            page_start=2, page_end=3, exclude_terms=["积分"])
        with patch.object(review_service, "generate_extraction", fake_extract):
            result = review_service.run_review(
                COURSE, "extract", self.TEXT, extract_type="points",
                with_answer=True, constraints=c)

        self.assertIsNotNone(result)
        self.assertNotIn("积分", result.markdown)
        self.assertEqual(result.metrics["validation"]["ok"], True)
        self.assertEqual(result.metrics["block_attempts"], 3)  # 第 1 块 2 次 + 第 2 块 1 次
        # 范围外的第 1 页不应送进模型
        self.assertTrue(all("第 1 页" not in call["chunk"] for call in calls))
        self.assertIn("第 2–3 页", calls[0]["block"])
        self.assertIn("积分", calls[0]["block"])
        # 重试时把违规说明回灌（并发下不一定是第 2 次调用）
        self.assertTrue(any("未通过" in call["note"] for call in calls), calls)
        self.assertNotIn("未通过", calls[0]["note"])

    def test_strict_violation_raises(self):
        c = TaskConstraints(task="extract", extract_type="points", page_start=2, page_end=3,
                            exclude_terms=["积分"], max_retries=2)
        with patch.object(review_service, "generate_extraction",
                          lambda *a, **k: "### 考点：积分技巧\n- [出处：《约束资料》第2页]\n"):
            with self.assertRaises(ConstraintViolation):
                review_service.run_review(COURSE, "extract", self.TEXT,
                                          extract_type="points", constraints=c)

    def test_non_strict_keeps_output(self):
        c = TaskConstraints(task="extract", extract_type="points", page_start=2, page_end=3,
                            exclude_terms=["积分"], max_retries=1, strict=False)
        with patch.object(review_service, "generate_extraction",
                          lambda *a, **k: "### 考点：积分技巧\n- [出处：《约束资料》第2页]\n"):
            result = review_service.run_review(COURSE, "extract", self.TEXT,
                                               extract_type="points", constraints=c)
        self.assertIsNotNone(result)
        self.assertFalse(result.metrics["validation"]["ok"])
        self.assertTrue(any("积分" in w for w in result.warnings), result.warnings)


def _paper(questions: int = 2) -> str:
    qs = "\n".join(f"{i}. 关于高阶导数的判断题，说明理由。" for i in range(1, questions + 1))
    answers = "\n".join(f"{i}. 理由略。" for i in range(1, questions + 1))
    return (f"# 约束集成测试 期末试卷\n**满分：100 分**\n\n"
            f"## 单项选择题（2 题，每题 50 分，共 100 分）\n{qs}\n\n"
            f"# 答案与解析\n{answers}\n")


class ExamServiceTest(unittest.TestCase):
    TEXT = "【《约束资料》第 1 页】\n高阶导数与隐函数求导。"

    def setUp(self):
        _ensure_course()

    def test_sections_blueprint_retry(self):
        calls: list[dict] = []

        def fake_exam(*args, **kwargs):
            calls.append(kwargs)
            # 第一次少一题 → 结构违规；第二次按约束补齐
            return _paper(1 if len(calls) == 1 else 2)

        sections = [{"name": "单项选择题", "count": 2, "points": 50}]
        with patch.object(review_service, "generate_exam_paper", fake_exam):
            result = review_service.run_review(
                COURSE, "exam", self.TEXT, sections=sections,
                user_context={"target_score": 80}, train_type="mock", num_sets=1,
                difficulty=3, with_answer=True)

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)
        self.assertIsNotNone(calls[0]["blueprint"])
        self.assertEqual(calls[0]["blueprint"].total, 100.0)
        self.assertIn("单项选择题", calls[0]["blueprint"].render())
        self.assertTrue(calls[1]["retry_note"])
        self.assertEqual(result.metrics["validation"]["ok"], True)
        self.assertEqual(result.metrics["validation"]["metrics"]["score_total"], 100.0)

    def test_wrong_structure_fails(self):
        sections = [{"name": "单项选择题", "count": 2, "points": 50}]
        c = TaskConstraints(task="exam", answer_mode="required", sections=sections,
                            max_retries=2)
        with patch.object(review_service, "generate_exam_paper",
                          lambda *a, **k: _paper(1)):
            with self.assertRaises(ConstraintViolation):
                review_service.run_review(COURSE, "exam", self.TEXT, sections=sections,
                                          constraints=c, with_answer=True)


class GuideServiceTest(unittest.TestCase):
    def setUp(self):
        _ensure_course()
        self.pptx = _make_pptx(["第一章 高阶导数", "第二章 参数方程", "第三章 相关变化率"])
        db = get_db_session()
        try:
            db.query(Material).filter(Material.course_id == 9001).delete()
            db.add(Material(course_id=9001, file_path=self.pptx, file_type="core",
                            weight=3, filename=Path(self.pptx).name))
            db.commit()
        finally:
            db.close()

    def _fake_generator(self, calls: list[dict], bad_times: int = 1):
        def _gen(raw_text, info, **kwargs):
            calls.append({"raw": raw_text, **kwargs})
            body = kwargs.get("chapter", {}).get("title", "章节")
            if len(calls) <= bad_times:
                return (f"## 核心考点：{body}\n\n### 1.1 积分中值定理\n\n"
                        "这里讲了积分的做法（P.2）。\n")
            return (f"## 核心考点：{body}\n\n### 1.1 高阶导数\n\n"
                    "只讲高阶导数（P.2）。\n")
        return _gen

    def test_scope_prompt_retry_and_gate(self):
        calls: list[dict] = []
        outline = Outline([Chapter(index=0, title="测试章", pages=[0, 1, 2])], source="test")
        c = TaskConstraints(task="guide", page_start=2, page_end=3, exclude_terms=["积分"])
        result = guide_service.run_guide(
            COURSE, mode="key", outline=outline, guide_generator=self._fake_generator(calls, 1),
            constraints=c, study_mode="exam")

        self.assertIsNotNone(result)
        self.assertEqual(len(calls), 2)  # 一次违规 + 一次修正
        self.assertNotIn("积分", result.markdown)
        self.assertEqual(result.metrics["validation"]["ok"], True)
        self.assertEqual(result.metrics["constraint_attempts"], 2)
        # 范围外的第 1 页不进提示词
        self.assertTrue(all("第 1 页" not in call["raw"] for call in calls))
        # 约束块确实带上了任务级约束
        self.assertIn("第 2–3 页", calls[0]["constraint_block"])
        self.assertIn("积分", calls[0]["constraint_block"])
        # 重试时把违规说明回灌
        self.assertIn("未通过", calls[1]["user_note"])

    def test_strict_violation_raises(self):
        outline = Outline([Chapter(index=0, title="测试章", pages=[0, 1])], source="test")
        c = TaskConstraints(task="guide", exclude_terms=["积分"])
        with self.assertRaises(ConstraintViolation):
            guide_service.run_guide(
                COURSE, mode="key", outline=outline,
                guide_generator=self._fake_generator([], bad_times=99),
                constraints=c)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class CoverageLedgerTest(unittest.TestCase):
    """覆盖率分母必须是资料页数，不是“块有没有产出”。"""

    def test_extract_coverage_is_page_based(self):
        import threading, time
        text = "\n\n".join(f"【《覆盖测试》第 {i} 页】\n第 {i} 页内容" for i in range(1, 11))

        def fake_extract(chunk, extract_type, with_answer, user_note="", constraint_block=""):
            m = __import__("re").search(r"第\s*(\d+)\s*页", chunk)
            page = int(m.group(1)) if m else 1
            if page <= 6:
                return f"### 考点：第{page}页考点\n- **是什么**：测试。\n- [出处：《覆盖测试》第{page}页]\n"
            return "【本段无题目】\n"

        c = TaskConstraints(task="extract", extract_type="points", max_retries=0)
        with patch.object(review_service, "generate_extraction", fake_extract):
            merged, coverage, report = review_service._run_extract(
                text, "points", True, lambda _e: None, threading.Event(), time.time(),
                constraints=c)
        self.assertEqual(coverage["pages"], 10)
        self.assertEqual(coverage["pages_cited"], 6)
        self.assertEqual(coverage["pages_missing"], [7, 8, 9, 10])
        self.assertAlmostEqual(coverage["coverage"], 0.6, places=3)
        self.assertTrue(coverage["has_page_headers"])


class SplitPagesTest(unittest.TestCase):
    def test_material_prefix_not_ghost_page(self):
        text = ("【重点资料·权重3：x.pptx】\n【《x.pptx》第 1 页】\nA\n\n"
                "【《x.pptx》第 2 页】\nB")
        pages = review_service.split_pages(text)
        self.assertEqual(len(pages), 2)
        self.assertIn("《x.pptx》第 1 页", pages[0])
        self.assertIn("重点资料", pages[0])


class CitationRepairTest(unittest.TestCase):
    def test_repairs_missing_citation_by_source_match(self):
        md = "### 考点：隐函数求导\n- 方程两边对 x 求导。\n"
        pages = ["【《有机化学【蜂考系统课】.pdf》第 3 页】\n隐函数求导：方程两边对 x 求导。"]
        out, fixed = review_service.repair_topic_citations(md, pages)
        self.assertEqual(fixed, 1)
        self.assertIn("（第3页）", out)

    def test_keeps_unmatched_for_hard_gate(self):
        md = "### 考点：完全无关的主题\n- 内容。\n"
        pages = ["【《有机化学【蜂考系统课】.pdf》第 3 页】\n隐函数求导：方程两边对 x 求导。"]
        out, fixed = review_service.repair_topic_citations(md, pages)
        self.assertEqual(fixed, 0)
        self.assertNotIn("第3页", out)


class OverviewCoverageTest(unittest.TestCase):
    def test_overview_is_labelled_not_page_coverage(self):
        cov = guide_service._coverage_metrics(
            "## 第一章\n本讲抽样：第3页\n",
            "【《数学分析》第 1 页】\n【《数学分析》第 2 页】\n【《数学分析》第 3 页】\n",
            True)
        self.assertEqual(cov["coverage_mode"], "overview_sample")
        self.assertEqual(cov["sampled_pages"], 1)
        self.assertIn("不是逐页", cov["coverage_note"])

    def test_full_mode_has_no_overview_label(self):
        cov = guide_service._coverage_metrics(
            "第1页 第2页 第3页", "【《x》第 1 页】\n【《x》第 2 页】\n【《x》第 3 页】", False)
        self.assertNotIn("coverage_mode", cov)
        self.assertAlmostEqual(cov["coverage"], 1.0)
