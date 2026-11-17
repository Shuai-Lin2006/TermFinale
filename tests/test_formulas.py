"""公式层：OCR 公式可搜索、可渲染，坏公式不硬塞。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.ingest.mineru_backend import extract_formulas
from tfv2.product import formulas as F


class ExtractTests(unittest.TestCase):
    def test_display_and_inline(self) -> None:
        md = "说明 $I_{BQ}=\\frac{U}{R}$ 正文\n\n$$U_{CEQ} = U_{CC} - I_{CQ}R_c$$\n\n仅 $\\beta$"
        rows = extract_formulas(md)
        latex = [r["latex"] for r in rows]
        self.assertIn("U_{CEQ} = U_{CC} - I_{CQ}R_c", latex)
        self.assertIn("I_{BQ}=\\frac{U}{R}", latex)
        self.assertTrue(any(r["display"] for r in rows))

    def test_duplicates_removed(self) -> None:
        rows = extract_formulas("$a+b$\n\n$c+d$\n\n$a+b$")
        self.assertEqual(len([r for r in rows if r["latex"] == "a+b"]), 1)


class LoadAndBlocksTests(unittest.TestCase):
    def test_load_missing_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(F.load_formulas(Path(td)), {})
        self.assertEqual(F.load_formulas(None), {})

    def test_load_groups_by_page(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "formulas.json").write_text(json.dumps({"formulas": [
                {"page": 2, "latex": "a+b", "display": True},
                {"page": 2, "latex": "c+d", "display": False},
                {"page": 3, "latex": "e", "display": True},
            ]}), encoding="utf-8")
            got = F.load_formulas(root)
        self.assertEqual(len(got[2]), 2)
        self.assertIn(3, got)

    def test_blocks_skip_invalid_latex(self) -> None:
        rows = [{"latex": "a+b", "display": True},
                {"latex": "", "display": True},
                {"latex": "x = {y", "display": True},          # 括号不闭合
                {"latex": "含中文的公式", "display": True}]      # 中文公式 KaTeX 会挂
        blocks = F.formula_blocks_for_page(local_page=1, orig_page=2, formulas=rows, material="m.pdf")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["kind"], "formula")
        self.assertEqual(blocks[0]["text"], "$$a+b$$")
        self.assertEqual(blocks[0]["source_refs"][0]["page_start"], 2)
        self.assertEqual(blocks[0]["doc_page"], 1)

    def test_blocks_limit(self) -> None:
        rows = [{"latex": f"a_{i}+b", "display": True} for i in range(10)]
        blocks = F.formula_blocks_for_page(local_page=1, orig_page=1, formulas=rows, material="m", limit=3)
        self.assertEqual(len(blocks), 3)
