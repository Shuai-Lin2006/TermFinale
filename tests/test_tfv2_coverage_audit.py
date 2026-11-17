"""逐页覆盖审计测试（Fake 模型）。"""
from __future__ import annotations

import unittest

from tfv2.domain.lecture import BlockKind, FigureRef, LectureBlock, LectureSection, SourceRef
from tfv2.domain.page import Page
from tfv2.quality.coverage_audit import audit_page, lecture_text_for_page


class FakeClient:
    def json(self, system: str, user: str, *, max_tokens: int = 4096, temperature: float = 0.35) -> dict:
        return {"points": [{"point": "定义", "covered": True, "evidence": "讲义有"}],
                "missing": [], "note": ""}


def section(page: int) -> LectureSection:
    return LectureSection(
        id="s", title="节",
        blocks=[LectureBlock(id="b", kind=BlockKind.PARAGRAPH, text="讲义内容",
                             source_refs=[SourceRef(material="资料.pdf", page_start=page, page_end=page)])],
        source_refs=[SourceRef(material="资料.pdf", page_start=page, page_end=page)],
    )


class CoverageAuditTests(unittest.TestCase):
    def test_covered_page(self) -> None:
        out = audit_page(FakeClient(), Page(material="资料.pdf", page_no=1, text="定义"), [section(1)])
        self.assertEqual(out.status, "covered")
        self.assertEqual(out.points[0].point, "定义")

    def test_visual_page(self) -> None:
        out = audit_page(FakeClient(), Page(material="资料.pdf", page_no=2, text=""), [section(2)])
        self.assertEqual(out.status, "visual")

    def test_overview_page(self) -> None:
        out = audit_page(FakeClient(), Page(material="资料.pdf", page_no=1, text="一、结构 二、性质"), [], overview=True)
        self.assertEqual(out.status, "overview")

    def test_page_context_only_includes_blocks_for_that_page(self) -> None:
        sec = LectureSection(
            id="s", title="节",
            blocks=[
                LectureBlock(id="a", kind=BlockKind.PARAGRAPH, text="第一页专属内容",
                             source_refs=[SourceRef(material="资料.pdf", page_start=1, page_end=1)]),
                LectureBlock(id="b", kind=BlockKind.PARAGRAPH, text="第二页专属内容",
                             source_refs=[SourceRef(material="资料.pdf", page_start=2, page_end=2)]),
            ],
            source_refs=[SourceRef(material="资料.pdf", page_start=1, page_end=2)],
        )
        text = lecture_text_for_page([sec], 1)
        self.assertIn("第一页专属内容", text)
        self.assertNotIn("第二页专属内容", text)

    def test_page_context_includes_figure_caption(self) -> None:
        fig = FigureRef(
            image_id="f", caption="第3页波形图", source=SourceRef(material="资料.pdf", page_start=3, page_end=3),
            after_block_id="fig", asset_path="assets/f.png",
        )
        sec = LectureSection(
            id="s", title="节",
            blocks=[
                LectureBlock(id="fig", kind=BlockKind.FIGURE, text="", figure=fig),
                LectureBlock(id="p", kind=BlockKind.PARAGRAPH, text="讲解",
                             source_refs=[SourceRef(material="资料.pdf", page_start=3, page_end=3)]),
            ],
            source_refs=[SourceRef(material="资料.pdf", page_start=3, page_end=3)],
        )
        text = lecture_text_for_page([sec], 3)
        self.assertIn("第3页波形图", text)

    def test_page_context_falls_back_to_section_refs(self) -> None:
        sec = LectureSection(
            id="s", title="节",
            blocks=[LectureBlock(id="a", kind=BlockKind.PARAGRAPH, text="整节兜底内容", source_refs=[])],
            source_refs=[SourceRef(material="资料.pdf", page_start=4, page_end=4)],
        )
        self.assertIn("整节兜底内容", lecture_text_for_page([sec], 4))

    def test_missing_without_section(self) -> None:
        out = audit_page(FakeClient(), Page(material="资料.pdf", page_no=3, text="定义"), [])
        self.assertEqual(out.status, "missing")


if __name__ == "__main__":
    unittest.main()
