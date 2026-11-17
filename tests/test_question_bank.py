"""Manual bank import + fallback when the model cannot extract."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tfv2.product import module_handlers, question_bank


class QuestionBankTests(unittest.TestCase):
    def test_csv_import_and_dedupe(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.csv"
            p.write_text("stem,answer,page,type\nQ1,A,1,choice\nQ1,B,1,choice\nQ2,C,2,short_answer\n", encoding="utf-8")
            root = Path(td) / "ws"
            out = question_bank.import_to_workspace(root, p)
            self.assertEqual(out["imported"], 2)
            self.assertEqual(len(question_bank.items(root)), 2)

    def test_material_filter(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.json"
            p.write_text('{"items":[{"stem":"A题","material_id":"a"},{"stem":"B题","material_id":"b"}]}', encoding="utf-8")
            root = Path(td) / "ws"
            question_bank.import_to_workspace(root, p)
            self.assertEqual([x["stem"] for x in question_bank.items(root, "a")], ["A题"])
            self.assertEqual([x["stem"] for x in question_bank.items(root, "b")], ["B题"])

    def test_json_import_requires_stem(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.json"
            p.write_text('{"items":[{"answer":"A"}]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                question_bank.load(p)

    def test_model_failure_uses_manual_bank(self):
        class Failing:
            def json(self, *a, **k):
                raise RuntimeError("down")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            question_bank.save(root, [{"stem": "人工题", "answer": "A", "source_page": 1}])
            handler = module_handlers.questions_handler(client=Failing(), bank_root=root)
            out = handler({"id": "x", "title": "x"})
            self.assertEqual(out["status"], "validated")
            self.assertEqual(out["source"], "manual_bank")
            self.assertEqual(out["items"], 1)

    def test_incomplete_bank_stays_partial(self):
        class Failing:
            def json(self, *a, **k):
                raise RuntimeError("down")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ws"
            question_bank.save(root, [{"stem": "人工题", "answer": "", "source_page": 1}])
            handler = module_handlers.questions_handler(client=Failing(), bank_root=root)
            out = handler({"id": "x", "title": "x"})
            self.assertEqual(out["status"], "partial")


if __name__ == "__main__":
    unittest.main()
