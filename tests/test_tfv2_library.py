"""讲义库扫描测试。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.library import discover


class LibraryTests(unittest.TestCase):
    def test_discovers_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "docs" / "evidence" / "demo"
            art.mkdir(parents=True)
            (art / "lecture.html").write_text("<html></html>", encoding="utf-8")
            (art / "lecture.pdf").write_bytes(b"%PDF")
            (art / "manifest.json").write_text(json.dumps({
                "artifact": "demo", "chapter": "第一章 测试", "pdf_pages": 12,
                "scope_coverage": "12/12 = 100%", "gate": {"passed": True},
                "section_count": 3, "figure_report": {"figures": 2},
                "generated_at": "2026-11-09 18:00",
            }, ensure_ascii=False), encoding="utf-8")
            items = discover(d)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].title, "第一章 测试")
            self.assertTrue(items[0].pdf_url)
            self.assertTrue(items[0].gate_passed)

    def test_missing_html_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / "docs" / "evidence" / "demo"
            art.mkdir(parents=True)
            (art / "manifest.json").write_text('{"artifact":"demo"}', encoding="utf-8")
            self.assertEqual(discover(d), [])


if __name__ == "__main__":
    unittest.main()
