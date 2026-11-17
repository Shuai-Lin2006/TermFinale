"""v2 讲义契约与门禁测试（Phase 0 基础）。"""
from __future__ import annotations

import unittest

from tfv2.domain.lecture import (
    BlockKind,
    FigureRef,
    LanguagePolicy,
    LectureBlock,
    LectureClosing,
    LectureFooter,
    LectureHeader,
    LectureSection,
    LectureSpec,
    LectureSummary,
    SourceRef,
    TocItem,
)
from tfv2.quality.lecture_gate import validate_lecture


def src(page: int = 1) -> SourceRef:
    return SourceRef(material="高数.pdf", page_start=page, page_end=page, quote="原文")


def make_spec(
    *,
    page_count: int = 100,
    coverage: float = 100.0,
    overview: bool = False,
) -> LectureSpec:
    section = LectureSection(
        id="s1",
        title="第一节 导数",
        blocks=[
            LectureBlock(
                id="b1",
                kind=BlockKind.PARAGRAPH,
                text="导数的定义与几何意义。",
                source_refs=[src(1)],
            )
        ],
        source_refs=[src(1)],
    )
    return LectureSpec(
        header=LectureHeader(
            title="高数讲义",
            course="高等数学",
            materials=["高数.pdf"],
            target_score=80,
            days_left=7,
            foundation="一般",
            persona="老师",
        ),
        toc=[TocItem(level=1, title="第一节 导数", page_no=1, anchor="s1")],
        summary=LectureSummary(overview="这份资料讲导数与微分。", knowledge_map=["导数", "微分"]),
        sections=[section],
        closing=LectureClosing(persona="老师", text="把这一章啃下来。"),
        footer=LectureFooter(coverage_percent=coverage, material_label="高数.pdf"),
        language_policy=LanguagePolicy(gen_lang="中文", source_lang="中文"),
        page_count=page_count,
        coverage_percent=coverage,
        overview_mode=overview,
    )


class LectureGateTests(unittest.TestCase):
    def test_valid_lecture_passes(self) -> None:
        report = validate_lecture(make_spec())
        self.assertTrue(report.passed, report.summary())

    def test_missing_toc_fails(self) -> None:
        spec = make_spec()
        spec.toc = []
        self.assertFalse(validate_lecture(spec).passed)

    def test_empty_section_fails(self) -> None:
        spec = make_spec()
        spec.sections[0].blocks = []
        self.assertFalse(validate_lecture(spec).passed)

    def test_section_without_source_fails(self) -> None:
        spec = make_spec()
        spec.sections[0].source_refs = []
        self.assertFalse(validate_lecture(spec).passed)

    def test_150_pages_requires_98_coverage(self) -> None:
        self.assertFalse(validate_lecture(make_spec(page_count=150, coverage=97.9)).passed)
        self.assertTrue(validate_lecture(make_spec(page_count=150, coverage=98.0)).passed)

    def test_150_pages_cannot_be_overview(self) -> None:
        self.assertFalse(validate_lecture(make_spec(page_count=150, coverage=100, overview=True)).passed)

    def test_151_pages_requires_overview(self) -> None:
        self.assertFalse(validate_lecture(make_spec(page_count=151, coverage=50, overview=False)).passed)
        self.assertTrue(validate_lecture(make_spec(page_count=151, coverage=50, overview=True)).passed)

    def test_footer_disclaimer_required(self) -> None:
        spec = make_spec()
        spec.footer.disclaimer = ""
        self.assertFalse(validate_lecture(spec).passed)

    def test_inline_page_citation_rejected(self) -> None:
        spec = make_spec()
        spec.sections[0].blocks[0].text = "如 P.3 所示，导数表示切线斜率。"
        report = validate_lecture(spec)
        self.assertFalse(report.passed)
        self.assertTrue(any(x.code == "body.px" for x in report.issues))

    def test_figure_requires_ref(self) -> None:
        spec = make_spec()
        spec.sections[0].blocks.append(
            LectureBlock(id="fig", kind=BlockKind.FIGURE, text="")
        )
        self.assertFalse(validate_lecture(spec).passed)

    def test_figure_with_caption_and_source_passes(self) -> None:
        spec = make_spec()
        spec.sections[0].blocks.append(
            LectureBlock(
                id="fig",
                kind=BlockKind.FIGURE,
                text="",
                figure=FigureRef(
                    image_id="img1",
                    caption="图 1 导数几何意义",
                    source=src(2),
                    after_block_id="fig",
                ),
            )
        )
        self.assertTrue(validate_lecture(spec).passed)

    def test_duplicate_section_titles_fail(self) -> None:
        spec = make_spec()
        spec.sections.append(
            LectureSection(
                id="s2",
                title="第一节 导数",
                blocks=[LectureBlock(id="b2", kind=BlockKind.PARAGRAPH, text="重复")],
                source_refs=[src(2)],
            )
        )
        self.assertFalse(validate_lecture(spec).passed)

    def test_duplicate_extension_marker_fails(self) -> None:
        spec = make_spec()
        spec.sections[0].blocks.append(
            LectureBlock(id="b2", kind=BlockKind.EXAMPLE,
                         text="【延伸】【延伸】例题：1+1=2", source_refs=[src(1)])
        )
        report = validate_lecture(spec)
        self.assertFalse(report.passed)
        self.assertTrue(any(x.code == "block.extension_dup" for x in report.issues))

    def test_source_page_out_of_range_fails(self) -> None:
        spec = make_spec(page_count=100)
        spec.sections[0].source_refs = [src(200)]
        self.assertFalse(validate_lecture(spec).passed)

    def test_scope_coverage_is_computed_from_sections(self) -> None:
        spec = make_spec(page_count=100, coverage=100)
        spec.scope_pages = [1, 2]
        spec.sections[0].source_refs = [src(1)]
        report = validate_lecture(spec)
        self.assertFalse(report.passed)
        self.assertTrue(any(x.code == "coverage.low" for x in report.issues))

        spec.sections[0].source_refs = [src(1), src(2)]
        spec.sections[0].blocks[0].source_refs = [src(1), src(2)]
        self.assertTrue(validate_lecture(spec).passed)

    def test_broad_section_refs_without_block_refs_fails(self) -> None:
        spec = make_spec(page_count=100, coverage=100)
        spec.scope_pages = [1, 2]
        spec.sections[0].source_refs = [src(1), src(2)]
        spec.sections[0].blocks[0].source_refs = [src(1)]
        report = validate_lecture(spec)
        self.assertFalse(report.passed)
        self.assertTrue(any(x.code == "coverage.blocks" for x in report.issues))


if __name__ == "__main__":
    unittest.main()


class LectureTextNormalizationTests(unittest.TestCase):
    def test_duplicate_titles_do_not_get_number_suffix(self) -> None:
        from tfv2.authoring.lecture import normalize_lecture_sections

        sections = [
            LectureSection(id="s1", title="刑法基本原则与罪刑法定",
                           blocks=[LectureBlock(id="b1", kind=BlockKind.PARAGRAPH,
                                                text="罪刑法定原则的含义与适用")],
                           source_refs=[src(1)]),
            LectureSection(id="s2", title="刑法基本原则与罪刑法定",
                           blocks=[LectureBlock(id="b2", kind=BlockKind.PARAGRAPH,
                                                text="罪责自负与主客观相统一")],
                           source_refs=[src(2)]),
        ]
        normalize_lecture_sections(sections, "zh")
        self.assertNotEqual(sections[0].title, sections[1].title)
        self.assertFalse(any("（2）" in s.title for s in sections))

    def test_visible_escaped_newline_is_cleaned(self) -> None:
        from tfv2.authoring.lecture import _sanitize_visible_text

        raw = "换路前的稳态：\\n(1) 求初始值；\\n解：先画等效电路。"
        text = _sanitize_visible_text(raw)
        self.assertNotIn("\\n", text)
        self.assertIn("\n(1)", text)
        self.assertIn("\n解：", text)

    def test_latex_command_is_not_mistaken_for_newline(self) -> None:
        from tfv2.authoring.lecture import _sanitize_visible_text

        self.assertEqual(_sanitize_visible_text(r"$\nabla f$"), r"$\nabla f$")

    def test_specific_last_title_is_not_overwritten_by_recap_rule(self) -> None:
        from tfv2.authoring.lecture import normalize_lecture_sections

        sections = [
            LectureSection(id="s1", title="换路定则", blocks=[
                LectureBlock(id="b1", kind=BlockKind.PARAGRAPH, text="换路定则与初始值")], source_refs=[src(1)]),
            LectureSection(id="s2", title="一阶电路三要素法", blocks=[
                LectureBlock(id="b2", kind=BlockKind.PARAGRAPH, text="三要素法公式与步骤")], source_refs=[src(2)]),
            LectureSection(id="s3", title="三要素法综合例题与作业布置", blocks=[
                LectureBlock(id="b3", kind=BlockKind.PARAGRAPH,
                             text="换路定则 一阶电路三要素法 综合复习与作业")], source_refs=[src(3)]),
        ]
        normalize_lecture_sections(sections, "zh")
        self.assertEqual(sections[-1].title, "三要素法综合例题与作业布置")
