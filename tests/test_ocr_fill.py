"""低文字页回填：优先本地 MinerU，云端 OCR 连续失败就停。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from tfv2.product import generate


def _ledger(texts: list[str]):
    pages = [type("P", (), {"page_no": i + 1, "text": t, "quality": None, "ocr_used": False})() for i, t in enumerate(texts)]
    return type("L", (), {"pages": pages})()


class OcrFillTests(unittest.TestCase):
    def _pdf(self, root: Path, pages: int = 3) -> Path:
        pdf = root / "scan.pdf"
        doc = pymupdf.open()
        for _ in range(pages):
            doc.new_page()
        doc.save(str(pdf))
        doc.close()
        return pdf

    def test_local_mineru_used_first(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pdf = self._pdf(Path(td))
            ledger = _ledger(["", ""])
            with patch("tfv2.ingest.mineru_backend.ocr_pdf_pages", return_value=({1: "本地OCR文字", 2: "第二页"}, "mineru")), \
                 patch("core.parser._ocr_page", side_effect=AssertionError("不该走云端")):
                generate._ocr_low_text(ledger, pdf)
        self.assertEqual([p.text for p in ledger.pages], ["本地OCR文字", "第二页"])

    def test_cloud_stops_after_two_failures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pdf = self._pdf(Path(td))
            ledger = _ledger(["", "", ""])
            calls = {"n": 0}

            def boom(page):
                calls["n"] += 1
                raise TimeoutError("timed out")

            with patch("tfv2.ingest.mineru_backend.ocr_pdf_pages", side_effect=RuntimeError("no mineru")), \
                 patch("core.parser._ocr_page", side_effect=boom):
                generate._ocr_low_text(ledger, pdf)
        self.assertEqual(calls["n"], 2, "云端连续失败两次后不再尝试")
