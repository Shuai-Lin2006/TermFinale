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
