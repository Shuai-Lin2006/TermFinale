"""Frontend regression checks that do not need a browser."""
import re
import unittest
from pathlib import Path


class NewCourseFormTests(unittest.TestCase):
    def _render_new(self) -> str:
        source = Path("web_v2/app.js").read_text(encoding="utf-8")
        start = source.index("function renderNew()")
        end = source.index("\n  function ", start)
        return source[start:end]

    def test_new_course_form_does_not_reference_edit_params(self) -> None:
        self.assertIsNone(re.search(r"\bep\.", self._render_new()),
                          "renderNew must not reference edit-only param variable ep")

    def test_new_course_form_has_no_lecture_prompts(self) -> None:
        # 新建课程只收课程信息与资料；讲义参数（目标分/剩余天数/基础）在生成时再定。
        segment = self._render_new()
        for name in ("persona", "illustrations", "key_points", "excluded", "custom_prompt"):
            self.assertNotIn(f'name="{name}"', segment)
        for name in ("target_score", "days_left", "foundation"):
            self.assertNotIn(f'name="{name}"', segment, "新建课程不应收集讲义参数")
        for name in ("mastery", "exam_date", "ai_preference"):
            self.assertIn(f'name="{name}"', segment)

    def test_new_course_derives_lecture_params_from_mastery(self) -> None:
        segment = self._render_new()
        self.assertIn('out.set("target_score"', segment)
        self.assertIn('out.set("foundation"', segment)
        self.assertIn('out.set("days_left"', segment)


class ExamNonQuestionTests(unittest.TestCase):
    def test_exam_has_explicit_non_question_checkbox(self) -> None:
        source = Path("web_v2/app.js").read_text(encoding="utf-8")
        self.assertIn("allow_non_question", source)
        self.assertIn("参考文件不是题目时", source)


class RecallModeTests(unittest.TestCase):
    def test_nouns_recall_mode_toggle_exists(self) -> None:
        source = Path("web_v2/app.js").read_text(encoding="utf-8")
        self.assertIn("默写模式", source)
        self.assertIn("recall-mode", source)


class GuidePageTests(unittest.TestCase):
    def test_guide_loads_three_tabs_from_content_file(self) -> None:
        source = Path("web_v2/app.js").read_text(encoding="utf-8")
        start = source.index("async function renderGuide")
        end = source.index("\n  function", start)
        segment = source[start:end]
        self.assertIn("/static/guide.json", segment)
        self.assertIn('id="guideBody"', segment)

    def test_guide_renders_steps_and_images(self) -> None:
        source = Path("web_v2/app.js").read_text(encoding="utf-8")
        start = source.index("function guideBodyHtml")
        end = source.index("async function renderGuide", start)
        segment = source[start:end]
        self.assertIn("guide-steps", segment)
        self.assertIn("guide-figure", segment)
        self.assertIn("guide.pendingTitle", source)


if __name__ == "__main__":
    unittest.main()


class FusionPanelTests(unittest.TestCase):
    """多资料拼接必须真的有 UI 入口，而不是只留一个后端接口。"""

    def _source(self) -> str:
        return Path("web_v2/app.js").read_text(encoding="utf-8")

    def test_panel_has_multi_select_and_mode_switch(self) -> None:
        source = self._source()
        self.assertIn("/api/lecture/fuse-jobs", source)
        self.assertIn('class="fuse-src"', source)
        self.assertIn('name="fuseMode"', source)
        self.assertIn('value="merge"', source)
        self.assertIn('value="separate"', source)
        self.assertNotIn("alert(", source.split("async function startFusion")[1].split("async function pollFuseJob")[0],
                         "拼接入口不允许用 alert 弹窗")

    def test_mode_copy_matches_product_rules(self) -> None:
        source = self._source()
        self.assertIn("拼接至少", source)          # 少于两份直接拒绝
        self.assertIn("不拼接", source)
        self.assertIn("act.startFusion", source)
        self.assertIn("    startFusion,", source)  # 已挂到 window.act


class FusionApiTests(unittest.TestCase):
    def test_route_is_registered(self) -> None:
        source = Path("tfv2/api/product_app.py").read_text(encoding="utf-8")
        self.assertIn('@app.post("/api/lecture/fuse-jobs")', source)
        self.assertIn("plan_materials", source)     # 档位交集在入口处校验


class PageUnitWiringTests(unittest.TestCase):
    """提取/练习/出卷必须能走 PageUnit，而不是只按讲文章节。"""

    def _source(self) -> str:
        return Path("web_v2/app.js").read_text(encoding="utf-8")

    def test_workbench_has_page_unit_mode(self) -> None:
        source = self._source()
        self.assertIn("/api/tasks/units", source)
        self.assertIn("act.wbSourceMode('pages')", source)
        self.assertIn('id="wbPages"', source)
        self.assertIn("按资料页", source)
        self.assertIn("function parsePageSpec", source)

    def test_skipped_formula_pages_are_reported_to_user(self) -> None:
        source = self._source()
        self.assertIn("skipped_pages", source)
        self.assertIn("wb.unitSkipped", source)

    def test_analysis_is_not_offered_for_page_mode(self) -> None:
        # 逻辑分析只针对讲文章节，按资料页提取时不能假装支持。
        source = self._source()
        segment = source.split("async function runUnitsTask")[1].split("async function pollTaskJob")[0]
        self.assertIn('w.kind === "analysis"', segment)


class TierPickerTests(unittest.TestCase):
    """档位弹窗必须由服务端规则驱动，且把覆盖目标和高成本讲清楚。"""

    def _picker(self) -> str:
        return Path("web_v2/picker.js").read_text(encoding="utf-8")

    def test_tiers_come_from_server_plan(self) -> None:
        source = self._picker()
        self.assertIn("/api/lecture/plan", source)
        self.assertIn("fetchPlan", source)
        # 前端不再自建 50/150/500 分档表
        self.assertNotIn("if (n <= 500)", source)

    def test_tier_modal_shows_coverage_and_cost(self) -> None:
        source = self._picker()
        for text in ("覆盖目标", "成本高", "资料共", "已选"):
            self.assertIn(text, source)
        self.assertIn("任何档位都不允许遗漏知识点", source)

    def test_plan_failure_is_surfaced_not_swallowed(self) -> None:
        source = self._picker()
        self.assertIn("planError", source)
        self.assertIn("档位没能从服务端读取", source)


class FusionTierIntersectionTests(unittest.TestCase):
    """拼接时必须把可用档位交集展示出来，没有交集要直接说不能拼。"""

    def _source(self) -> str:
        return Path("web_v2/app.js").read_text(encoding="utf-8")

    def test_panel_asks_plan_api_for_intersection(self) -> None:
        source = self._source()
        segment = source.split("async function fuseRecalc")[1].split("async function startFusion")[0]
        self.assertIn("/api/lecture/plan", segment)
        self.assertIn("merge_tiers", segment)
        self.assertIn("merge: true", segment)

    def test_no_intersection_copy_is_explicit(self) -> None:
        source = self._source()
        self.assertIn("fuse.tiersNone", source)
        self.assertIn("没有交集，不能拼接", source)

    def test_recalc_wired_to_controls(self) -> None:
        source = self._source()
        self.assertIn('onchange="act.fuseRecalc()"', source)
        self.assertIn('id="fuseTiers"', source)


class PracticePageUnitTests(unittest.TestCase):
    """练习按资料页出题时，公式/图片页被跳过必须告诉用户。"""

    def test_api_reports_skipped_pages(self) -> None:
        source = Path("tfv2/api/product_app.py").read_text(encoding="utf-8")
        segment = source.split('def practice_source(')[1].split("@app.post")[0]
        self.assertIn("practice_from_units", segment)
        self.assertIn("skipped_pages", segment)

    def test_ui_toasts_skipped_pages(self) -> None:
        source = Path("web_v2/app.js").read_text(encoding="utf-8")
        self.assertIn("practice.skippedPages", source)
        self.assertIn("data.skipped_pages", source)


class UnitExamUiTests(unittest.TestCase):
    """出卷也要能直接按资料页出（走 /api/exam/units），并说明跳过页。"""

    def _source(self) -> str:
        return Path("web_v2/app.js").read_text(encoding="utf-8")

    def test_papers_tab_has_page_based_exam(self) -> None:
        source = self._source()
        self.assertIn('id="unitExamPages"', source)
        self.assertIn("/api/exam/units", source)
        self.assertIn("async function startUnitExam", source)
        self.assertIn("    startUnitExam,", source)

    def test_skipped_pages_are_reported(self) -> None:
        source = self._source()
        segment = source.split("async function startUnitExam")[1].split("async function startFusion")[0]
        self.assertIn("skipped_pages", segment)
        self.assertIn("exam.unitSkipped", segment)


class TextModeUiTests(unittest.TestCase):
    def test_picker_offers_text_mode_and_sends_it(self) -> None:
        src = Path("web_v2/picker.js").read_text(encoding="utf-8")
        self.assertIn('id="tfTextMode"', src)
        self.assertIn("tf-textmode-", src)
        self.assertIn("text_mode:", src)
        self.assertIn("扫描件用本地 OCR 的文字排版", src)


class ArtifactMetricsUiTests(unittest.TestCase):
    """产物页要能直接看到质量指标，而不是只躺在 JSON 里。"""

    def _source(self) -> str:
        return Path("web_v2/app.js").read_text(encoding="utf-8")

    def test_artifact_page_fetches_and_renders_metrics(self) -> None:
        source = self._source()
        seg = source[source.index("async function renderArtifact"):]
        seg = seg[:seg.index("async function", 10)]
        self.assertIn("/metrics", seg)
        self.assertIn("metricsRow", seg)
        for key in ("quality.citationSupport", "quality.termRecall",
                    "quality.dupSentence", "quality.boilerplate"):
            self.assertIn(key, source)
        self.assertIn("quality.metricsHint", source)

    def test_image_mode_has_its_own_line(self) -> None:
        source = self._source()
        self.assertIn("quality.imageModeDetail", source)


class CoverageTargetUiTests(unittest.TestCase):
    def test_metrics_row_shows_tier_coverage(self) -> None:
        src = Path("web_v2/app.js").read_text(encoding="utf-8")
        self.assertIn("quality.coverageMet", src)
        self.assertIn("quality.coverageNoTier", src)
        self.assertIn("coverage_target", src)


class JobResumeUiTests(unittest.TestCase):
    """失败之后要能“接着做”，而不是只能重头再来。"""

    def _src(self) -> str:
        return Path("web_v2/app.js").read_text(encoding="utf-8")

    def test_failure_shows_next_step_and_resume(self) -> None:
        src = self._src()
        self.assertIn("job.failedNext", src)
        self.assertIn("job.resume", src)
        self.assertIn("resumeJob", src)
        seg = src[src.index("async function resumeJob"):]
        seg = seg[:seg.index("function resumeAgent")]
        self.assertIn("/api/exam/jobs/", seg)
        self.assertIn("/api/lectures/jobs/", seg)
        self.assertIn("/resume", seg)


class AuditButtonUiTests(unittest.TestCase):
    def test_artifact_page_has_audit_action(self) -> None:
        src = Path("web_v2/app.js").read_text(encoding="utf-8")
        self.assertIn("artifact.runAudit", src)
        self.assertIn("/audit", src)
        self.assertIn("runArtifactAudit", src)
