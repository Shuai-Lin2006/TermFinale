"""产物复核入口：没有复核记录的讲义要能一键复核并刷新状态。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from tfv2.api import product_app


def _art(root: Path) -> Path:
    art = root / "art"
    art.mkdir()
    for name, data in {
        "sections.json": [{"id": "s1", "title": "章", "blocks": [], "source_refs": []}],
        "manifest.json": {"gate": {"passed": True}},
        "lecture.html": "<html></html>",
        "lecture.pdf": "",
    }.items():
        path = art / name
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_text(json.dumps(data), encoding="utf-8")
    return art


class AuditEndpointTests(unittest.TestCase):
    def test_audit_runs_and_refreshes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _art(Path(td))
            with patch.object(product_app.service, "artifact_path", return_value=art), \
                 patch("tfv2.quality.artifact_audit.audit_artifact_dir",
                       return_value=[{"page_no": 1, "status": "covered"}]), \
                 patch.object(product_app.service, "refresh_artifact_gate", return_value={}), \
                 patch.object(product_app.service, "get_artifact",
                              return_value={"delivery": {"status": "delivered"}, "quality": {}}):
                got = product_app.artifact_audit("aid")
        self.assertEqual(got["counts"]["covered"], 1)
        self.assertEqual(got["status"], "delivered")

    def test_missing_artifact_404(self) -> None:
        with patch.object(product_app.service, "artifact_path", return_value=None):
            with self.assertRaises(HTTPException):
                product_app.artifact_audit("none")

    def test_without_sections_422(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = Path(td) / "art"
            art.mkdir()
            with patch.object(product_app.service, "artifact_path", return_value=art):
                with self.assertRaises(HTTPException):
                    product_app.artifact_audit("aid")
