"""Four modules must select independently, never cross-contaminate."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tfv2.product import workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name) / "ws"
        workspace.create(self.root, "高数", [
            {"id": "a", "title": "教材", "pages": 35},
            {"id": "b", "title": "真题", "pages": 8},
        ])

    def tearDown(self):
        self.td.cleanup()

    def test_modules_are_independent(self):
        workspace.select(self.root, "lecture", ["a"])
        workspace.select(self.root, "extract", ["b"])
        workspace.select(self.root, "questions", ["a", "b"])
        workspace.select(self.root, "exam", ["b"])
        self.assertEqual([m["id"] for m in workspace.resolve(self.root, "lecture")], ["a"])
        self.assertEqual([m["id"] for m in workspace.resolve(self.root, "extract")], ["b"])
        self.assertEqual([m["id"] for m in workspace.resolve(self.root, "questions")], ["a", "b"])
        self.assertEqual([m["id"] for m in workspace.resolve(self.root, "exam")], ["b"])
        # changing lecture does not change extract
        workspace.select(self.root, "lecture", ["b"])
        self.assertEqual([m["id"] for m in workspace.resolve(self.root, "extract")], ["b"])

    def test_unknown_material_rejected(self):
        with self.assertRaises(workspace.WorkspaceError):
            workspace.select(self.root, "extract", ["missing"])

    def test_lecture_only_one(self):
        with self.assertRaises(workspace.WorkspaceError):
            workspace.select(self.root, "lecture", ["a", "b"])


if __name__ == "__main__":
    unittest.main()
