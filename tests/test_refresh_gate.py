"""复核结果不能覆盖结构门禁：页面要分开显示“结构完整”和“复核范围”。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tfv2.product import service


def _art(root: Path, gate_passed: bool = True) -> Path:
    art = root / "art"
    art.mkdir()
    (art / "manifest.json").write_text(json.dumps({"gate": {"passed": gate_passed, "issues": []}}),
                                       encoding="utf-8")
    (art / "coverage_audit.json").write_text(json.dumps([
        {"page_no": 1, "status": "covered"},
        {"page_no": 2, "status": "partial"},
        {"page_no": 3, "status": "unverified"},
    ]), encoding="utf-8")
    return art


class RefreshGateTests(unittest.TestCase):
    def test_audit_does_not_flip_structure_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _art(Path(td))
            with patch.object(service, "artifact_path", return_value=art):
                service.refresh_artifact_gate("aid")
            man = json.loads((art / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(man["gate"]["passed"], "复核有 partial 不该把结构门禁改成未通过")
        self.assertEqual(man["coverage_audit"]["partial"], 1)
        self.assertEqual(man["coverage_audit"]["unverified"], 1)
