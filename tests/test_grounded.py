"""证据优先：伪造引文必须被删，真实引文与讲解保留。"""
from __future__ import annotations

import unittest

from core.generate.evidence_pack import build_pack
from core.generate.grounded import validate_quotes

PAGES = ["【《高数》第 1 页】\n隐函数求导：方程两边对 x 求导，再解出 y'。"]


class GroundedTest(unittest.TestCase):
    def test_real_quote_kept_fake_dropped(self):
        pack = build_pack(PAGES)
        md = ("## 核心考点：隐函数\n\n"
              "> 原文：隐函数求导：方程两边对 x 求导，再解出 y'。（P.1）\n"
              "**讲解**：见到 y 就补 y'。\n\n"
              "> 原文：这里编了一句话（P.1）\n"
              "**讲解**：这是假的。\n")
        out, kept, dropped = validate_quotes(md, pack)
        self.assertIn("隐函数求导", out)
        self.assertIn("见到 y", out)
        self.assertNotIn("编了一句", out)
        self.assertEqual((kept, dropped), (1, 1))

    def test_metadata_quote_rejected(self):
        pack = build_pack(PAGES)
        md = "> 原文：【《高数》第 1 页】隐函数求导（P.1）\n**讲解**：假引文。\n"
        out, kept, dropped = validate_quotes(md, pack)
        self.assertEqual(kept, 0)
        self.assertEqual(dropped, 1)

    def test_empty_section_removed(self):
        from core.generate.grounded import _remove_empty_sections
        md = "## 核心考点：导数\n\n### 空小节\n\n### 有内容\n\n> 原文：隐函数求导（P.1）\n**讲解**：讲。\n"
        out = _remove_empty_sections(md)
        self.assertNotIn("空小节", out)
        self.assertIn("有内容", out)

    def test_unique_quote_count(self):
        from core.generate.grounded import _unique_quotes
        md = ("> 原文：甲（P.1）\n> 原文：甲（P.1）\n> 原文：乙（P.2）\n")
        self.assertEqual(_unique_quotes(md), 2)
