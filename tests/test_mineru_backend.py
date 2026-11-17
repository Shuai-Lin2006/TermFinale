"""本地 MinerU 后端：没装要说明原因，跑通要能缓存，别偷偷空转。"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from tfv2.ingest import mineru_backend


def _pdf(path: Path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((60, 80), "scan placeholder", fontsize=12)
    doc.save(str(path))
    doc.close()
    return path


class MinerUBackendTests(unittest.TestCase):
    def test_missing_binary_reports_reason(self) -> None:
        with patch.dict("os.environ", {"TFV2_MINERU_BIN": "/nonexistent/mineru"}):
            ok, reason = mineru_backend.available()
        self.assertFalse(ok)
        self.assertIn("TFV2_MINERU_BIN", reason)

    def test_parse_strips_markers_and_caches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = _pdf(root / "a.pdf")
            fake_bin = root / "mineru"
            fake_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            fake_bin.chmod(0o755)
            calls = {"n": 0}

            def fake_run(cmd, **kwargs):
                calls["n"] += 1
                out = Path(cmd[cmd.index("-o") + 1])
                out.write_text("<!-- page 1 of 2 -->\n一、选择题\n1. 题干\n<!-- page 2 of 2 -->\n2. 题干",
                               encoding="utf-8")
                return subprocess.CompletedProcess(cmd, 0, "", "")

            with patch.dict("os.environ", {"TFV2_MINERU_BIN": str(fake_bin)}), \
                    patch.object(mineru_backend, "CACHE_DIR", root / "cache"), \
                    patch.object(mineru_backend.subprocess, "run", side_effect=fake_run):
                text = mineru_backend.ocr_pdf_text(pdf)
                self.assertNotIn("<!-- page", text)
                self.assertIn("一、选择题", text)
                first = calls["n"]
                again = mineru_backend.ocr_pdf_text(pdf)
                self.assertEqual(again, text)
                self.assertEqual(calls["n"], first, "第二次应命中缓存，不再跑模型")

    def test_empty_output_raises_with_reason(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = _pdf(root / "a.pdf")
            fake_bin = root / "mineru"
            fake_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            fake_bin.chmod(0o755)

            def fake_run(cmd, **kwargs):
                return subprocess.CompletedProcess(cmd, 1, "", "No engine available")

            with patch.dict("os.environ", {"TFV2_MINERU_BIN": str(fake_bin)}), \
                    patch.object(mineru_backend, "CACHE_DIR", root / "cache"), \
                    patch.object(mineru_backend.subprocess, "run", side_effect=fake_run):
                with self.assertRaises(mineru_backend.MinerUError) as ctx:
                    mineru_backend.ocr_pdf_text(pdf)
            self.assertIn("No engine available", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()


class FormulaCacheTests(unittest.TestCase):
    """老缓存没有 formulas 时要重解析，而不是返回空公式。"""

    def test_old_cache_triggers_reparse(self) -> None:
        import json, tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tfv2.ingest import mineru_backend as M

        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "a.pdf"
            pdf.write_bytes(b"%PDF-1.4 fake")
            cache = M._cache_path(pdf, "doc")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"pages": {"1": "旧文本"}, "headings": []}), encoding="utf-8")
            with patch.object(M, "available", return_value=(True, "/bin/true")), \
                 patch.object(M, "ocr_pdf_pages", return_value=({1: "文本"}, "mineru")), \
                 patch.object(M, "_ensure_server"), \
                 patch.object(M.subprocess, "run") as run:
                run.return_value = type("R", (), {"returncode": 0})()
                out = M.ocr_pdf_document(pdf)
        self.assertIn("formulas", out)
        run.assert_called_once()
