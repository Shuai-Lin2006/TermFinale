"""单段生成失败也要交：用资料原文兜底，并留下原因。"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from tfv2.product.generate import _source_fallback_section


class SectionFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = SimpleNamespace(material="高数.pdf")
        self.pages = {
            1: SimpleNamespace(text="函数在一点的极限存在，要求左右极限相等。"),
            2: SimpleNamespace(text="   "),
        }

    def test_text_page_becomes_source_block(self) -> None:
        sec = _source_fallback_section(self.ledger, self.pages, 2, "第 2 节", [1, 2], "模型超时")
        self.assertEqual(sec.title, "第 2 节")
        self.assertEqual(len(sec.blocks), 2)
        self.assertIn("资料原文（第 1 页）", sec.blocks[0].text)
        self.assertIn("空白页或纯图片", sec.blocks[1].text)
        self.assertIn("模型超时", sec.summary or "")

    def test_every_page_has_source_ref(self) -> None:
        sec = _source_fallback_section(self.ledger, self.pages, 1, "第 1 节", [1, 2], "失败")
        cited = {ref.page_start for ref in sec.blocks[0].source_refs} | {ref.page_start for ref in sec.blocks[1].source_refs}
        self.assertEqual(cited, {1, 2})
        self.assertEqual({r.page_start for r in sec.source_refs}, {1, 2})

    def test_missing_page_still_covered(self) -> None:
        sec = _source_fallback_section(self.ledger, self.pages, 3, "第 3 节", [2, 9], "失败")
        self.assertEqual(len(sec.blocks), 2)
        self.assertIn("第 9 页", sec.blocks[1].text)
