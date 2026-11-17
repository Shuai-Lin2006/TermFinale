"""Round 4 audit: partial lecture must be exportable."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tfv2.api import product_app
from tfv2.product import service


class PartialExportTests(unittest.TestCase):
    def test_partial_lecture_exports_html(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "artifacts"
            art = root / "partial_art"
            art.mkdir(parents=True)
            (art / "manifest.json").write_text(
                '{"chapter":"部分讲义","draft":true,"gate":{"passed":false,"issues":[{"severity":"hard"}]}}',
                encoding="utf-8")
            (art / "lecture.html").write_text("<html><body>部分内容</body></html>", encoding="utf-8")
            (art / "sections.json").write_text('[{"id":"s1","title":"第一节","blocks":[]}]', encoding="utf-8")
            old = service.ARTIFACT_ROOTS
            service.ARTIFACT_ROOTS = [root]
            try:
                q = service._quality("partial_art", art, __import__("json").loads((art / "manifest.json").read_text()))
                self.assertEqual(q["status"], "partial")
                view = service._view("partial_art", art, __import__("json").loads((art / "manifest.json").read_text()))
                self.assertTrue(view["delivery"]["exportable"])
                req = SimpleNamespace(base_url="http://127.0.0.1:8907/")
                resp = product_app.artifact_export_html("partial_art", req)
                body = resp.body.decode("utf-8")
                self.assertIn("部分内容", body)
            finally:
                service.ARTIFACT_ROOTS = old


if __name__ == "__main__":
    unittest.main()
