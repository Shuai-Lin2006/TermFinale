"""Artifact audit writes coverage_audit.json."""
from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from tfv2.quality.artifact_audit import audit_artifact_dir


class Tests(unittest.TestCase):
    def test_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                audit_artifact_dir(Path(td) / "missing")


if __name__ == "__main__":
    unittest.main()
