"""Round 16: table header repeat and row integrity."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

from tfv2.render.docx import _add_md_table
from tfv2.render.lecture_html import _md_table_html


def _long_table(rows: int = 24) -> str:
    lines = ["| 序号 | 名称 | 说明 |", "| --- | --- | --- |"]
    for i in range(rows):
        lines.append(f"| {i+1} | 条目{i+1} | 这是用于跨页测试的说明文字 |")
    return "\n".join(lines)


class TableRenderTests(unittest.TestCase):
    def test_html_has_repeatable_thead(self):
        html = _md_table_html(_long_table(3))
        self.assertIn("<thead>", html)
        self.assertIn("</thead><tbody>", html)
        self.assertIn("<th>序号</th>", html)

    def test_word_header_repeats_and_rows_do_not_split(self):
        with tempfile.TemporaryDirectory() as td:
            doc = Document()
            _add_md_table(doc, _long_table(3))
            path = Path(td) / "table.docx"
            doc.save(str(path))
            loaded = Document(str(path))
            table = loaded.tables[0]
            first_tr = table.rows[0]._tr
            self.assertIsNotNone(first_tr.find(qn("w:trPr")).find(qn("w:tblHeader")))
            for row in table.rows:
                self.assertIsNotNone(row._tr.find(qn("w:trPr")).find(qn("w:cantSplit")))


if __name__ == "__main__":
    unittest.main()
