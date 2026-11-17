"""根因优化：模型漏页时补原文，而不是整节判失败。"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef
from tfv2.product.generate import _accept_issue, _fill_missing_pages


def _section(text: str, page: int = 1) -> LectureSection:
    return LectureSection(
        id="s", title="章",
        blocks=[LectureBlock(id="b1", kind=BlockKind.PARAGRAPH, text=text,
                             source_refs=[SourceRef(material="m.pdf", page_start=page, page_end=page)])],
        source_refs=[SourceRef(material="m.pdf", page_start=page, page_end=page)],
    )


class FillMissingPagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = SimpleNamespace(material="高数.pdf")
        self.pages = {
            1: SimpleNamespace(text="函数极限的定义。"),
            2: SimpleNamespace(text="极限存在的判定条件。"),
            3: SimpleNamespace(text="   "),
        }

    def test_text_page_filled_from_source(self) -> None:
        sec = _section("函数极限的定义。", 1)
        filled = _fill_missing_pages(sec, [1, 2, 3], self.pages, self.ledger, 1)
        self.assertEqual(filled, [2, 3], "返回补了哪些页，用来统计漏页比例")
        texts = [b.text for b in sec.blocks]
        self.assertTrue(any(t.startswith("资料补充（第 2 页）") for t in texts))
        self.assertTrue(any("空白页或图片页" in t for t in texts))

    def test_second_call_does_not_duplicate(self) -> None:
        sec = _section("函数极限的定义。", 1)
        _fill_missing_pages(sec, [1, 2, 3], self.pages, self.ledger, 1)
        count = len(sec.blocks)
        again = _fill_missing_pages(sec, [1, 2, 3], self.pages, self.ledger, 1)
        self.assertEqual(len(sec.blocks), count)
        self.assertEqual(again, [], "已经补过的页不再重复计")

    def test_section_without_refs_gets_them(self) -> None:
        sec = _section("函数极限的定义。", 1)
        sec.source_refs = []
        _fill_missing_pages(sec, [1, 2], self.pages, self.ledger, 1)
        self.assertEqual({r.page_start for r in sec.source_refs}, {1, 2})

    def test_cited_pages_untouched(self) -> None:
        sec = _section("函数极限的定义。", 1)
        filled = _fill_missing_pages(sec, [1], self.pages, self.ledger, 1)
        self.assertEqual(filled, [])
        self.assertEqual(len(sec.blocks), 1)


class AcceptIssueTests(unittest.TestCase):
    def test_single_high_weight_term_retried_first_time(self) -> None:
        sec = _section("极限出现一次。")
        self.assertIn("只出现一次", _accept_issue(sec, [("极限", 5)], attempt=0))

    def test_second_attempt_accepts(self) -> None:
        sec = _section("极限出现一次。")
        self.assertEqual(_accept_issue(sec, [("极限", 5)], attempt=1), "")

    def test_no_weight_no_issue(self) -> None:
        self.assertEqual(_accept_issue(_section("任意"), [], attempt=0), "")


class PipelineSanitizeOrderTests(unittest.TestCase):
    """生成流程必须在最终写 sections.json 前做公式收口（否则 PDF 门禁会挂）。"""

    def test_sanitize_runs_before_final_write(self) -> None:
        from pathlib import Path
        source = Path("tfv2/product/generate.py").read_text(encoding="utf-8")
        start = source.index("def generate_lecture(")
        seg = source[start:]
        idx_sanitize = seg.index("sanitize_section_math")
        last_write = seg.rindex('(out / "sections.json").write_text')
        self.assertLess(idx_sanitize, last_write, "收口必须发生在最后一次写盘之前")


class ConciseModeTest(unittest.TestCase):
    """简洁成文模式必须只靠环境变量开启，并真的写进提示词。"""

    def test_concise_note_gated_by_env(self) -> None:
        from pathlib import Path
        src = Path("tfv2/product/generate.py").read_text(encoding="utf-8")
        self.assertIn("TERMFINALE_CONCISE_SECTIONS", src)
        self.assertIn("1200 字以内", src)
