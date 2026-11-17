"""错题复习改用 FSRS 排程：稳定性要涨、间隔要拉开。"""
from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from tfv2.product import store


class FsrsStoreTests(unittest.TestCase):
    def test_review_advances_stability_and_due_date(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with patch.object(store, "DB_PATH", Path(td) / "p.sqlite3"):
                mid = store.upsert_mistake({
                    "id": "q-1", "question_id": "q-1", "artifact_id": "a", "section": "s",
                    "stem": "题干", "options": ["A", "B", "C", "D"], "answer": 0,
                    "explanation": "解析", "page": 1,
                }, review_in_days=0)
                first = store.review_mistake(mid, True)
                self.assertGreater(first["stability"], 0, "记住一次后应有稳定性")
                self.assertGreaterEqual(date.fromisoformat(first["next_review"][:10]), date.today() + timedelta(days=1))
                second = store.review_mistake(mid, True)
                self.assertGreater(second["stability"], first["stability"], "连续记住，稳定性应上升")
                forgot = store.review_mistake(mid, False)
                self.assertGreater(forgot["lapses"], 0, "忘记要计入 lapses")
                self.assertLess(forgot["stability"], second["stability"], "忘记后稳定性下降")

    def test_due_and_forecast_shape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with patch.object(store, "DB_PATH", Path(td) / "p.sqlite3"):
                store.upsert_mistake({
                    "id": "q-2", "question_id": "q-2", "artifact_id": "a", "section": "s",
                    "stem": "题干2", "options": ["A", "B"], "answer": 0,
                    "explanation": "解析", "page": 1,
                }, review_in_days=0)
                due = store.review_due(limit=10)
                self.assertEqual([d["question_id"] for d in due], ["q-2"])
                rows = store.review_forecast(days=7)
                self.assertEqual(len(rows), 7)
                self.assertIn("date", rows[0])
