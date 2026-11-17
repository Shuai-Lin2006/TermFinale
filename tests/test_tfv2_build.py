"""通用构建 CLI 测试（不跑 PDF）。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.build import build_project


class BuildTests(unittest.TestCase):
    def test_build_project_without_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            sections = [{
                "id": "s", "title": "第一节", "level": 2,
                "blocks": [{"id": "b", "kind": "paragraph", "text": "这是正文，长度足够。", "source_refs": [
                    {"material": "x.pptx", "page_start": 1, "page_end": 1}]}],
                "source_refs": [{"material": "x.pptx", "page_start": 1, "page_end": 1}],
            }]
            (base / "sections.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
            project = {
                "id": "demo", "chapter_title": "第一章 测试",
                "header": {"title": "第一章 测试", "course": "测试课"},
                "summary": {"overview": "摘要"},
                "closing": {"persona": "老师", "text": "结语"},
                "footer": {"coverage_percent": 100, "material_label": "x.pptx"},
                "sections_files": ["sections.json"], "page_count": 1, "coverage_percent": 100,
                "scope_pages": [1], "out_dir": "out",
            }
            (base / "project.json").write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
            result = build_project(base / "project.json", pdf=False)
            self.assertEqual(result["sections"], 1)
            self.assertTrue((base / "out" / "lecture.html").is_file())
            self.assertTrue((base / "out" / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
