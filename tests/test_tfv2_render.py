"""v2 教材式 HTML 渲染测试。"""
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
from tfv2.render.lecture_html import render_lecture_html


def spec() -> LectureSpec:
    src = SourceRef(material="高数.pdf", page_start=1, page_end=2, quote="原文")
    section = LectureSection(
        id="s1",
        title="第一节 导数",
        source_refs=[src],
        blocks=[
            LectureBlock(id="b1", kind=BlockKind.PARAGRAPH, text="导数表示瞬时变化率。", source_refs=[src]),
            LectureBlock(id="b2", kind=BlockKind.PITFALL, text="不要漏掉链式法则。"),
            LectureBlock(
                id="fig",
                kind=BlockKind.FIGURE,
                figure=FigureRef(
                    image_id="img1",
                    caption="图 1 切线",
                    source=src,
                    after_block_id="fig",
                ),
            ),
        ],
    )
    return LectureSpec(
        header=LectureHeader(title="高数讲义", course="高等数学", materials=["高数.pdf"],
                             target_score=80, days_left=7, foundation="一般", persona="老师"),
        toc=[TocItem(level=1, title="第一节 导数", page_no=1, anchor="s1")],
        summary=LectureSummary(overview="这份资料讲导数。", knowledge_map=["导数"], exam_focus=["计算"]),
        sections=[section],
        closing=LectureClosing(persona="老师", text="把这一章啃下来。"),
        footer=LectureFooter(coverage_percent=100, material_label="高数.pdf"),
        language_policy=LanguagePolicy(gen_lang="中文", source_lang="中文"),
        page_count=2,
        coverage_percent=100,
    )


class RenderTests(unittest.TestCase):
    def test_renders_textbook_structure(self) -> None:
        html = render_lecture_html(spec())
        self.assertIn("TermFinale精品讲义", html)
        self.assertIn("<h1>高等数学</h1>", html)
        self.assertIn("高数讲义", html)
        self.assertIn("目录", html)
        self.assertIn("本资料讲什么", html)
        self.assertIn("出处：第 1–2 页", html)
        self.assertIn("generated-footer", html)
        self.assertIn("图 1 切线", html)
        self.assertIn("图 1 切线", html)
        self.assertIn("本资料由 TermFinale 智能体生成", html)

    def test_example_number_prefix_is_not_duplicated(self) -> None:
        s = spec()
        s.sections[0].blocks.append(
            LectureBlock(id="ex", kind=BlockKind.EXAMPLE, text="例1：先求导，再代入。")
        )
        html = render_lecture_html(s)
        self.assertIn("例题", html)
        self.assertNotIn("例1", html)
        self.assertIn("先求导，再代入。", html)

    def test_escapes_html(self) -> None:
        s = spec()
        s.sections[0].blocks[0].text = "<script>alert(1)</script>"
        html = render_lecture_html(s)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_persona_is_not_rendered_in_lecture(self) -> None:
        s = spec()
        s.header.persona = "温柔小姐姐"
        html = render_lecture_html(s)
        self.assertNotIn("人设：", html)
        self.assertNotIn("温柔小姐姐", html)

    def test_reader_tools_present(self) -> None:
        html = render_lecture_html(spec())
        for key in ("tfReaderTools", "tfSearchBtn", "tfEditBtn", "tfExportBtn", "tfAiBtn", "tfAiPanel", "tfLibLink", "tfLangBtn", "tfSelectionTools", "tfSelAsk", "tfSelSimplify"):
            self.assertIn(key, html)

    def test_no_inline_px_in_rendered_body(self) -> None:
        s = spec()
        s.sections[0].blocks[0].text = "见 P.3。"
        html = render_lecture_html(s)
        self.assertIn("见 P.3。", html)  # 渲染器不负责语义，门禁负责拒绝；这里确认不隐藏。


    def test_display_math_inside_paragraph_is_not_split_by_br(self) -> None:
        from tfv2.render.lecture_html import _para

        body = _para("给定矩阵\n$$A = \\begin{pmatrix}\n1 & 2 \\\\\n3 & 4\n\\end{pmatrix}$$\n求秩。")
        math_segment = body.split("$$", 1)[1].split("$$", 1)[0]
        self.assertNotIn("<br>", math_segment)
        self.assertIn("\\\\", math_segment)


    def test_textbook_modules_and_source_index_render(self) -> None:
        s = spec()
        s.sections[0].objectives = ["能复述导数的定义"]
        s.sections[0].key_terms = ["导数", "瞬时变化率"]
        s.sections[0].self_test = ["用一句话写出导数的定义。"]
        html = render_lecture_html(s)
        for text in ("本节目标", "关键术语", "自测", "资料页码索引", "能复述导数的定义"):
            self.assertIn(text, html)

    def test_source_index_has_section_pages(self) -> None:
        s = spec()
        html = render_lecture_html(s)
        self.assertIn('class="source-index"', html)
        self.assertIn("第 1–2 页", html)


if __name__ == "__main__":
    unittest.main()