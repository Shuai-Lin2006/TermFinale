"""Round 12: question metadata + CSV/Anki exports."""
from __future__ import annotations

import csv
import io
import unittest

from tfv2.product import exports, tasks


DOC = {"title": "2023 期末卷", "kind": "extract_questions", "content": {"items": [{
    "no": "1", "year": "2023", "exam": "期末", "source_no": "2", "qtype": "choice",
    "stem": "交感神经兴奋时", "options": ["心率加快", "心率减慢", "瞳孔缩小", "支气管收缩"],
    "answer": 0, "answer_text": "A", "analysis": "交感兴奋心率加快", "points": 5,
    "source_page": 3, "quote": "交感神经兴奋时心率加快",
}]}}


class ExportTests(unittest.TestCase):
    def test_question_csv_has_metadata(self):
        text = exports.questions_csv(DOC)
        rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
        self.assertEqual(rows[0][:4], ["no", "year", "exam", "source_no"])
        self.assertEqual(rows[1][1], "2023")
        self.assertEqual(rows[1][9], "5")
        self.assertEqual(rows[1][3], "2")

    def test_anki_csv_front_back(self):
        text = exports.anki_csv(DOC)
        rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
        self.assertEqual(rows[0], ["Front", "Back", "Tags"])
        self.assertIn("交感神经兴奋时", rows[1][0])
        self.assertIn("A", rows[1][1])
        self.assertIn("TermFinale", rows[1][2])

    def test_csv_injection_is_escaped(self):
        doc = {"kind": "paper", "content": {"questions": [{"stem": "=cmd", "analysis": "x"}]}}
        self.assertIn("'=cmd", exports.questions_csv(doc))


class MetadataTests(unittest.TestCase):
    def test_year_and_points(self):
        meta = tasks._question_meta({"year": "2022", "points": "5"}, "题干", "3")
        self.assertEqual(meta["year"], "2022")
        self.assertEqual(meta["points"], 5.0)

    def test_year_from_stem_when_missing(self):
        meta = tasks._question_meta({}, "2021 年真题：求导数", "1")
        self.assertEqual(meta["year"], "2021")

    def test_invented_year_is_removed_when_not_in_source(self):
        raw = {"qtype": "choice", "stem": "交感神经兴奋时", "options": ["A", "B", "C", "D"],
               "answer": 0, "analysis": "交感兴奋", "source_page": 1, "source_no": "1",
               "year": "2025"}
        item, issue = tasks._question_item(raw, {1}, {1: "交感神经兴奋时心率加快。"}, "original", 1)
        self.assertIsNone(issue)
        self.assertEqual(item["year"], "")


if __name__ == "__main__":
    unittest.main()
