"""Beta profile must not claim release or hide questions."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.product import launch_profile


def make(root: Path, missing=None):
    for m in ("lecture", "extract", "exam", "questions"):
        d = root / "outputs" / m; d.mkdir(parents=True)
        for i in ("a", "b"):
            if m == missing:
                continue
            status = "partial" if m == "questions" else "validated"
            (d / f"{i}.json").write_text(json.dumps({"status": status}), encoding="utf-8")


class LaunchProfileTests(unittest.TestCase):
    def test_beta_with_three_modules(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make(root)
            out = launch_profile.evaluate(root)
            self.assertEqual(out["mode"], "beta")
            self.assertFalse(out["release"])
            self.assertFalse(out["ui"])
            self.assertEqual(out["enabled"], ["lecture", "extract", "exam"])
            self.assertFalse(out["questions"]["enabled"])

    def test_not_ready_when_module_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); make(root, missing="exam")
            out = launch_profile.evaluate(root)
            self.assertEqual(out["mode"], "not_ready")
            self.assertIn("exam", out["disabled"])


if __name__ == "__main__":
    unittest.main()
