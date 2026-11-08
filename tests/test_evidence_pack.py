"""证据句库：先有原句，再过滤无依据段落。"""
from __future__ import annotations

import unittest

from core.generate.evidence_pack import build_pack, filter_unsupported, render_pack

PAGES = [
    "【《高数》第 1 页】\n隐函数求导：方程两边对 x 求导，再解出 y'。\n这是隐函数求导的核心步骤。",
    "【《高数》第 2 页】\n参数方程求导：dy/dx=(dy/dt)/(dx/dt)。",
]


class PackTest(unittest.TestCase):
    def test_build_and_render(self):
        pack = build_pack(PAGES)
        self.assertGreaterEqual(len(pack), 3)
        self.assertTrue(all(1 <= e.page <= 2 for e in pack))
        self.assertIn("隐函数求导", render_pack(pack))

    def test_filter_drops_unsupported(self):
        pack = build_pack(PAGES)
        md = ("## 核心考点：导数\n\n"
              "隐函数求导：方程两边对 x 求导，再解出 y'。\n\n"
              "量子力学波函数坍缩与薛定谔方程是另一门课。\n")
        out, kept, dropped = filter_unsupported(md, pack)
        self.assertIn("隐函数求导", out)
        self.assertNotIn("量子力学", out)
        self.assertEqual(dropped, 1)

    def test_material_prefix_not_evidence(self):
        pages = ["【重点资料·权重3：高数.pdf】\n【《高数.pdf》第 1 页】\n隐函数求导：方程两边对 x 求导。"]
        pack = build_pack(pages)
        self.assertTrue(pack)
        self.assertFalse(any("重点资料" in e.quote for e in pack))
