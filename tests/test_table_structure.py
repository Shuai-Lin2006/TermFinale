"""Round 15: table structure parse/normalize."""
from __future__ import annotations

import unittest

from tfv2.render import table_structure
from tfv2.render.lecture_html import _text_with_tables


TABLES = [
    "| 神经 | 作用 |\n| --- | --- |\n| 交感 | 心率加快 |\n| 副交感 | 心率减慢 |",
    "| 药物 | 剂量 | 备注 |\n| --- | --- | --- |\n| A | 5mg | 饭后 |",
    "| 年份 | 题号 | 分值 |\n| --- | --- | --- |\n| 2023 | 1 | 5 |\n| 2024 | 2 | 10 |",
    "| 名称 | 值 |\n| --- | --- |\n| a | 1 |",
]


class TableStructureTests(unittest.TestCase):
    def test_parse_valid_tables(self):
        for md in TABLES:
            parsed = table_structure.parse_pipe_table(md)
            self.assertIsNotNone(parsed, md)
            self.assertGreaterEqual(len(parsed["headers"]), 2)

    def test_malformed_table_rejected(self):
        md = "| a | b |\n| --- | --- |\n| 1 | 2 | 3 |"
        self.assertIsNone(table_structure.parse_pipe_table(md))
        self.assertFalse(table_structure.table_quality(md)["ok"])

    def test_normalize_keeps_rows(self):
        out = table_structure.normalize_table(TABLES[0])
        self.assertIn("| 交感 | 心率加快 |", out)
        self.assertIn("| --- | --- |", out)

    def test_real_exam_score_table_with_empty_cells(self):
        md = ("| 题 号 | 一 | 二 | 三 | 四 | 五 | 六 | 七 | 八 | 九 | 十 | 总 分 |\n"
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
              "| 得 分 |  |  |  |  |  |  |  |  |  |  |  |")
        q = table_structure.table_quality(md)
        self.assertTrue(q["ok"], q)
        self.assertEqual(q["cols"], 12)
        self.assertEqual(q["rows"], 1)

    def test_html_renders_real_table(self):
        html = _text_with_tables("见下表\n" + TABLES[0])
        self.assertIn("<table", html)
        self.assertIn("心率加快", html)


if __name__ == "__main__":
    unittest.main()
