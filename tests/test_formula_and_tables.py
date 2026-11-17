
"""Formula gate + Docling table application."""
from __future__ import annotations

import unittest

from tfv2.domain.page import Page, PageLedger, PageQuality
from tfv2.product.generate import _apply_docling_text, _latex_ok


class FormulaGateTests(unittest.TestCase):
    def test_clean_latex_passes(self) -> None:
        self.assertTrue(_latex_ok(r"\int_{0}^{1}{\frac{x^{2}}{\sqrt{1-x^{2}}}}\,dx={\frac{\pi}{4}}"))

    def test_hallucinated_latex_rejected(self) -> None:
        self.assertFalse(_latex_ok(r"\frac{\stackrel{\parallel}{\Big\vert}\Big\vert}{\Big\vert}\underbrace{\Theta\bigotimes}"))
        self.assertFalse(_latex_ok(r"\left|\left(\mathrm{alrccoS}\chi\right)'=-\frac{\mathrm{i}}{\sqrt{\mathrm{i}-X^{2}}}\right|"))
        self.assertFalse(_latex_ok("plain text"))


class MarkdownTableTests(unittest.TestCase):
    def test_pipe_table_to_html(self) -> None:
        from tfv2.render.lecture_html import _text_with_tables
        html = _text_with_tables("表格如下\n| 名称 | 值 |\n| --- | --- |\n| a | 1 |")
        self.assertIn("<table", html)
        self.assertIn("<th>名称</th>", html)
        self.assertIn("<td>1</td>", html)

    def test_plain_text_untouched(self) -> None:
        from tfv2.render.lecture_html import _text_with_tables
        self.assertNotIn("<table", _text_with_tables("普通段落"))


class DoclingTableTests(unittest.TestCase):
    def test_tables_appended_to_page_text(self) -> None:
        ledger = PageLedger(
            material="m", page_count=1, pages=[Page(material="m", page_no=1, text="正文段落")],
            source_hash="x", parser_version="1",
        )
        structure = {"provider": "docling", "pages": [{
            "page": 1, "width": 100, "height": 100,
            "blocks": [{"kind": "paragraph", "text": "正文段落", "bbox": [0, 10, 100, 30]}],
            "tables": [{"text": "| 名称 | 值 |\n| --- | --- |\n| a | 1 |", "bbox": [0, 40, 100, 60]}],
        }]}
        _apply_docling_text(ledger, structure)
        self.assertIn("[表格]", ledger.pages[0].text)
        self.assertIn("| 名称 | 值 |", ledger.pages[0].text)
        self.assertEqual(ledger.pages[0].quality, PageQuality.TEXT)


class ReferenceBankTests(unittest.TestCase):
    def test_bank_parse_shape(self) -> None:
        from tfv2.product.exam import _reference_bank

        class FakeClient:
            def json(self, system, user, **kw):
                return {"items": [{"no": "1", "type": "choice", "points": "5", "topic": "导数"}]}

        # 必须是真正的题卷文本（题号 + 选项/答案），否则会被“非题目文件”守卫拦下。
        bank = _reference_bank(FakeClient(), "一、选择题\n1. 求导 5分\nA. 1 B. 2 C. 3 D. 4\n答案：B\n2. 积分\nA. 1 B. 2 C. 3 D. 4\n答案：A")
        self.assertTrue(bank["used"])
        self.assertEqual(bank["items"][0]["no"], "1")

    def test_bank_empty_without_text(self) -> None:
        from tfv2.product.exam import _reference_bank
        bank = _reference_bank(None, "")
        self.assertFalse(bank["used"])
        self.assertEqual(bank["items"], [])


if __name__ == "__main__":
    unittest.main()
