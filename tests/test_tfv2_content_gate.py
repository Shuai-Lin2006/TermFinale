"""内容体检门禁测试。"""
from __future__ import annotations

import unittest

from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef
from tfv2.domain.page import Page, PageLedger
from tfv2.quality.content_gate import _pdf_text_for_scan, scan_lecture, scan_pages
from tests.test_tfv2_lecture import make_spec, src


def with_text(text: str, kind: BlockKind = BlockKind.PARAGRAPH):
    spec = make_spec()
    spec.sections[0].blocks = [LectureBlock(id="b", kind=kind, text=text, source_refs=[src(1)])]
    return spec


class ContentGateTests(unittest.TestCase):
    def test_mojibake_is_hard(self) -> None:
        report = scan_lecture(with_text("这里出现�替换符和锟斤拷"))
        self.assertFalse(report.passed)
        self.assertTrue(any(x.code == "text.mojibake" for x in report.issues))

    def test_raw_tex_outside_formula_is_hard(self) -> None:
        report = scan_lecture(with_text("这里直接写了 \\frac{1}{2} 没有公式标记"))
        self.assertFalse(report.passed)
        self.assertTrue(any(x.code == "text.raw_tex" for x in report.issues))

    def test_simple_formula_is_ok(self) -> None:
        report = scan_lecture(with_text("角张力 $\\frac{109.5-60}{2}$ 很简单"))
        self.assertTrue(report.passed)

    def test_complex_formula_is_warning(self) -> None:
        report = scan_lecture(with_text("$$\\frac{\\frac{\\frac{a}{b}}{c}}{d}$$"))
        self.assertTrue(report.passed)
        self.assertTrue(any(x.code == "formula.complex" for x in report.issues))

    def test_pdf_text_drops_katex_pua_but_keeps_controls(self) -> None:
        cleaned = _pdf_text_for_scan("公式\u200b字符\ue020正常\x01")
        self.assertNotIn("\u200b", cleaned)
        self.assertNotIn("\ue020", cleaned)
        self.assertIn("\x01", cleaned)

    def test_page_text_mojibake(self) -> None:
        ledger = PageLedger(material="x.pdf", page_count=1,
                            pages=[Page(material="x.pdf", page_no=1, text="Ã¤Â¸Â­")],
                            source_hash="sha256:x", parser_version="test")
        report = scan_pages(ledger)
        self.assertFalse(report.passed)


if __name__ == "__main__":
    unittest.main()
