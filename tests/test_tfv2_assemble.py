"""v2 讲义装配测试。"""
from __future__ import annotations

import unittest

from tfv2.authoring.assemble import build_lecture_spec
from tfv2.domain.lecture import (
    BlockKind,
    LectureBlock,
    LectureClosing,
    LectureFooter,
    LectureHeader,
    LectureSection,
    LectureSummary,
    SourceRef,
)
from tfv2.quality.lecture_gate import validate_lecture


class AssembleTests(unittest.TestCase):
    def test_toc_has_unique_anchors_and_gate_passes(self) -> None:
        src = SourceRef(material="资料.pdf", page_start=1, page_end=2)
        sec = LectureSection(
            id="s1", title="第一节",
            blocks=[LectureBlock(id="b1", kind=BlockKind.PARAGRAPH, text="正文", source_refs=[src])],
            source_refs=[src],
        )
        spec = build_lecture_spec(
            chapter_title="第一章",
            header=LectureHeader(title="讲义", course="课程"),
            summary=LectureSummary(overview="摘要"),
            sections=[sec],
            closing=LectureClosing(persona="老师", text="结语"),
            footer=LectureFooter(coverage_percent=100, material_label="资料.pdf"),
            page_count=2, coverage_percent=100, scope_pages=[1, 2],
        )
        self.assertEqual([t.level for t in spec.toc], [1, 2])
        self.assertEqual(len({t.anchor for t in spec.toc}), 2)
        self.assertTrue(validate_lecture(spec).passed)


if __name__ == "__main__":
    unittest.main()
