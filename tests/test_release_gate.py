"""Release gate: partial never ships."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.product import release_gate


class ReleaseGateTests(unittest.TestCase):
    def test_all_validated_release(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for m in release_gate.MODULES:
                d = root / "outputs" / m; d.mkdir(parents=True)
                for i in ("a", "b"):
                    (d / f"{i}.json").write_text(json.dumps({"status": "validated"}), encoding="utf-8")
            out = release_gate.evaluate(root, ui_ready=True, benchmark_passed=True)
            self.assertTrue(out["release"], out["blockers"])

    def test_partial_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for m in release_gate.MODULES:
                d = root / "outputs" / m; d.mkdir(parents=True)
                for i in ("a", "b"):
                    status = "partial" if m == "questions" else "validated"
                    (d / f"{i}.json").write_text(json.dumps({"status": status}), encoding="utf-8")
            out = release_gate.evaluate(root, ui_ready=True, benchmark_passed=True)
            self.assertFalse(out["release"])
            self.assertTrue(any("questions" in x for x in out["blockers"]))


if __name__ == "__main__":
    unittest.main()
