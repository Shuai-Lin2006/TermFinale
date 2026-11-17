"""图源报告测试。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tfv2.domain.lecture import (
    BlockKind, FigureRef, LectureBlock, LectureClosing, LectureFooter, LectureHeader,
    LectureSection, LectureSpec, LectureSummary, SourceRef,
)
from tfv2.quality.figure_report import build_figure_report


def make_spec(asset: str) -> LectureSpec:
    sec = LectureSection(
        id="s", title="一节",
        blocks=[LectureBlock(id="b", kind=BlockKind.FIGURE, text="",
                             figure=FigureRef(image_id="fig", caption="图 1 示意",
                                              source=SourceRef(material="资料.pdf", page_start=1, page_end=2),
                                              after_block_id="b", asset_path=asset))],
        source_refs=[SourceRef(material="资料.pdf", page_start=1, page_end=2)],
    )
    return LectureSpec(
        header=LectureHeader(title="讲义", course="课程"),
        summary=LectureSummary(overview="摘要"),
        sections=[sec], closing=LectureClosing(persona="老师", text="结语"),
        footer=LectureFooter(coverage_percent=100, material_label="资料.pdf"),
        page_count=2, coverage_percent=100, scope_pages=[1, 2],
    )


class FigureReportTests(unittest.TestCase):
    def test_existing_schematic_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fig.png"
            Image.new("RGB", (120, 80), "white").save(p)
            items = build_figure_report(make_spec("fig.png"), d)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].status, "ok_schematic")
            self.assertEqual((items[0].width, items[0].height), (120, 80))

    def test_missing_asset_fails(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            items = build_figure_report(make_spec("missing.png"), d)
            self.assertEqual(items[0].status, "fail")
            self.assertIn("资产不存在", items[0].issue or "")


if __name__ == "__main__":
    unittest.main()
