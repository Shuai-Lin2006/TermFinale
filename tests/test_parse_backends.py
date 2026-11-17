"""解析后端：auto 只在文字层不够时才上 MinerU，强制指定失败必须报原因。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from tfv2.ingest import backends


def _pdf(path: Path, text_per_page: int) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((60, 80), "x" * max(1, text_per_page), fontsize=10)
    doc.save(str(path))
    doc.close()
    return path


class ParseBackendTests(unittest.TestCase):
    def test_pymupdf_backend_never_calls_mineru(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pdf = _pdf(Path(td) / "a.pdf", 500)
            with patch.object(backends, "pymupdf_pages", return_value={1: "正文" * 100}), \
                    patch("tfv2.ingest.mineru_backend.ocr_pdf_document",
                          side_effect=AssertionError("不应调用 MinerU")):
                out = backends.parse_pdf(pdf, backend="pymupdf")
        self.assertEqual(out["engine"], "pymupdf")
        self.assertEqual(out["headings"], [])

    def test_auto_keeps_text_layer_when_enough(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pdf = _pdf(Path(td) / "a.pdf", 500)
            with patch.object(backends, "pymupdf_pages", return_value={1: "正" * 300, 2: "文" * 120}), \
                    patch("tfv2.ingest.mineru_backend.ocr_pdf_document",
                          side_effect=AssertionError("文字层够用时不调 MinerU")):
                out = backends.parse_pdf(pdf, backend="auto")
        self.assertEqual(out["engine"], "pymupdf")

    def test_auto_falls_back_to_mineru_and_says_why(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pdf = _pdf(Path(td) / "a.pdf", 1)
            fake = {"pages": {1: "OCR 文字"}, "headings": [{"page": 1, "level": 1, "text": "第一章"}],
                    "engine": "mineru-local"}
            with patch.object(backends, "pymupdf_pages", return_value={1: ""}), \
                    patch("tfv2.ingest.mineru_backend.ocr_pdf_document", return_value=fake):
                out = backends.parse_pdf(pdf, backend="auto")
        self.assertIn("mineru", out["engine"])
        self.assertIn("扫描件", out.get("fallback_reason", ""))
        self.assertEqual(out["headings"][0]["text"], "第一章")

    def test_forced_mineru_marks_forced(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pdf = _pdf(Path(td) / "a.pdf", 500)
            fake = {"pages": {1: "OCR"}, "headings": [], "engine": "mineru-local"}
            with patch("tfv2.ingest.mineru_backend.ocr_pdf_document", return_value=fake):
                out = backends.parse_pdf(pdf, backend="mineru")
        self.assertTrue(out.get("forced"))

    def test_unknown_backend_rejected(self) -> None:
        with self.assertRaises(ValueError):
            backends.parse_pdf("x.pdf", backend="magic")

    def test_env_default_is_auto(self) -> None:
        with patch.dict("os.environ", {"TFV2_PARSE_BACKEND": ""}):
            self.assertEqual(backends.configured_backend(), "auto")
        with patch.dict("os.environ", {"TFV2_PARSE_BACKEND": "mineru"}):
            self.assertEqual(backends.configured_backend(), "mineru")


if __name__ == "__main__":
    unittest.main()
