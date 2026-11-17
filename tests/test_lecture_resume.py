"""Round 6: lecture resume must reuse completed sections."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pymupdf

from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef
from tfv2.product import generate, service


class LectureResumeTests(unittest.TestCase):
    def test_resume_skips_completed_section(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.pdf"
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 72), "神经传导：动作电位沿轴突传播。")
            doc.save(str(source))
            doc.close()
            out = root / "artifact"
            (out / "source").mkdir(parents=True)
            (out / "source" / "source.pdf").write_bytes(source.read_bytes())
            section = LectureSection(
                id="s1", title="第一章 神经",
                blocks=[LectureBlock(id="b1", kind=BlockKind.PARAGRAPH,
                                     text="动作电位沿轴突传播。",
                                     source_refs=[SourceRef(material="source.pdf", page_start=1, page_end=1)])],
                source_refs=[SourceRef(material="source.pdf", page_start=1, page_end=1)],
            )
            checkpoint = {
                "source": str(source), "aid": out.name,
                "params": {"title": "续跑", "course": "医学", "target_score": 80, "days_left": 7,
                           "foundation": "基础一般", "persona": "老师", "key_points": "",
                           "excluded": "", "custom_prompt": "", "gen_lang": "zh", "illustrations": False},
                "plan": [["第一章 神经", [1]]],
                "sections": {"1": section.model_dump(mode="json")},
            }
            (out / "lecture_checkpoint.json").write_text(json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(generate, "interpret_requirements", lambda *a, **k: {"coverage": "all", "instructions": [], "must_cover": [], "must_not": []}), \
                 mock.patch.object(generate, "author_section", side_effect=AssertionError("resume called author_section")), \
                 mock.patch.object(generate, "author_section_titles", lambda *a, **k: []), \
                 mock.patch.object(generate, "author_section_meta", lambda *a, **k: None), \
                 mock.patch.object(generate, "author_wrapup", lambda *a, **k: SimpleNamespace(overview="续跑", knowledge_map=[], closing="完成")), \
                 mock.patch.object(generate, "fallback_wrapup", lambda *a, **k: SimpleNamespace(overview="续跑", knowledge_map=[], closing="完成")), \
                 mock.patch.object(generate, "_attach_figures", lambda sec, *a, **k: sec), \
                 mock.patch.object(generate, "_make_knowledge_map", lambda *a, **k: None), \
                 mock.patch.object(generate, "build_project", lambda *a, **k: None), \
                 mock.patch.object(service, "get_artifact", lambda aid: {"id": aid, "sections": 1}):
                result = generate.generate_lecture(
                    source, title="续跑", course="医学", gen_lang="zh",
                    resume_dir=out, checkpoint_path=out / "lecture_checkpoint.json",
                )
            self.assertEqual(result["id"], out.name)


if __name__ == "__main__":
    unittest.main()
