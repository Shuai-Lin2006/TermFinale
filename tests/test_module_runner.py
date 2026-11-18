"""2 materials x 4 modules: outputs must not cross."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.product import module_runner, workspace


class ModuleRunnerTests(unittest.TestCase):
    def test_two_materials_four_modules_no_cross(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            workspace.create(root, "demo", [
                {"id": "a", "title": "教材", "pages": 35},
                {"id": "b", "title": "真题", "pages": 8},
            ])
            workspace.select(root, "lecture", ["a"])
            workspace.select(root, "extract", ["b"])
            workspace.select(root, "questions", ["a", "b"])
            workspace.select(root, "exam", ["b"])

            def handler(material):
                return {"material": material["id"], "module": "x"}

            expected = {"lecture": ["a"], "extract": ["b"],
                        "questions": ["a", "b"], "exam": ["b"]}
            for module, ids in expected.items():
                out = module_runner.run(root, module, handler)
                self.assertEqual(out["selected"], ids)
                self.assertTrue(out["all_done"])
                for m in ids:
                    path = root / "outputs" / module / f"{m}.json"
                    self.assertTrue(path.is_file())
                    data = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(data["module"], module)
                    self.assertEqual(data["material_id"], m)

    def test_unselected_module_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            workspace.create(root, "demo", [{"id": "a"}])
            with self.assertRaises(module_runner.ModuleRunError):
                module_runner.run(root, "lecture", lambda m: {})


if __name__ == "__main__":
    unittest.main()
