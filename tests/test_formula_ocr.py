"""公式 OCR 层：本地脚本不可用就返回空，不编公式；能拿到时按页归位。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from tfv2.ingest import formula_ocr


class FormulaOcrTests(unittest.TestCase):
    def _pdf(self, root: Path) -> Path:
        pdf = root / "scan.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((80, 90), "U / R", fontsize=18)
        doc.save(str(pdf))
        doc.close()
        return pdf

    def test_unavailable_returns_empty(self) -> None:
        with patch.object(formula_ocr, "available", return_value=False):
            self.assertEqual(formula_ocr.ocr_pdf_formulas("x.pdf", "/tmp/x"), {})

    def test_latex_filter(self) -> None:
        self.assertTrue(formula_ocr.latex_ok("U_{CEQ} = U_{CC} - I_{CQ}R_c"))
        self.assertFalse(formula_ocr.latex_ok(""))
        self.assertFalse(formula_ocr.latex_ok("x = {y"))
        self.assertFalse(formula_ocr.latex_ok("\\Big( x \\Big)"))
        self.assertFalse(formula_ocr.latex_ok("含中文"))

    def test_pipeline_maps_pages_and_filters(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = self._pdf(root)
            work = root / "work"
            calls = {"n": 0}

            def fake_run(cmd, **kwargs):
                calls["n"] += 1
                if "formula_detect.py" in cmd[1]:
                    # 用真实渲染出来的页面图当检测输入
                    page_img = Path(cmd[2])
                    out = {"images": [{"path": str(page_img),
                                       "boxes": [{"xyxy": [60, 70, 220, 120], "cls": "isolated", "conf": 0.9},
                                                 {"xyxy": [0, 0, 5, 5], "cls": "isolated", "conf": 0.9}]}]}
                    return type("R", (), {"returncode": 0, "stdout": json.dumps(out)})()
                items = [{"path": path, "latex": "U_{CEQ} = U_{CC} - I_{CQ}R_c"} for path in cmd[2:]]
                items.append({"path": "bad.png", "latex": "x = {y"})
                return type("R", (), {"returncode": 0, "stdout": json.dumps({"items": items})})()

            with patch.object(formula_ocr, "_python", return_value="/bin/python"), \
                 patch.object(formula_ocr.subprocess, "run", side_effect=fake_run):
                got = formula_ocr.ocr_pdf_formulas(pdf, work)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(got.get(1), ["U_{CEQ} = U_{CC} - I_{CQ}R_c"], "坏公式要挡掉")
