"""审计驱动的逐点补讲：只补缺的点、带出处、可重新复核。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tfv2.domain.page import Page
from tfv2.product import topup


def _artifact(root: Path) -> Path:
    art = root / "art"
    art.mkdir()
    sections = [{
        "id": "s1", "title": "第一节",
        "blocks": [{"id": "b1", "kind": "paragraph", "text": "已有内容。",
                    "source_refs": [{"material": "m.pdf", "page_start": 1, "page_end": 1}]}],
        "source_refs": [{"material": "m.pdf", "page_start": 1, "page_end": 2}],
    }]
    (art / "sections.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (art / "project.json").write_text(json.dumps({"id": "art", "sections_files": ["sections.json"]}),
                                     encoding="utf-8")
    (art / "source_pages.json").write_text(json.dumps({
        "material": "m.pdf", "pages": [
            {"page": 1, "text": "第一页原文：极限的定义与性质。"},
            {"page": 2, "text": "第二页原文：连续函数的定义与一致连续性。"},
        ]}, ensure_ascii=False), encoding="utf-8")
    return art


class _FakeClient:
    def json(self, system, user, **kwargs):
        return {"points": [{"point": "一致连续性", "text": "一致连续要求 δ 与点无关。"},
                           {"point": "", "text": "这段太短"}]}


class TopupTests(unittest.TestCase):
    def test_topup_adds_blocks_for_partial_pages(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td))
            audits = {
                1: {"page_no": 1, "status": "covered", "points": [], "missing": []},
                2: {"page_no": 2, "status": "partial", "points": [], "missing": ["一致连续性", "连续定义"]},
            }

            def fake_audit(client, page: Page, sections):
                class R:
                    def model_dump(self_inner):
                        return audits[page.page_no]
                return R()

            with patch.object(topup.coverage_audit, "audit_page", side_effect=fake_audit), \
                 patch.object(topup, "audit_artifact_dir", return_value=[
                     {"page_no": 1, "status": "covered"}, {"page_no": 2, "status": "covered"}]), \
                 patch("tfv2.build.build_project"):
                got = topup.topup_artifact("art", artifact_path=art, client=_FakeClient())
            sections = json.loads((art / "sections.json").read_text(encoding="utf-8"))
            texts = [b["text"] for b in sections[0]["blocks"]]
            has_topup_file = (art / "topup.json").is_file()
        self.assertEqual(got["added"], 1)
        self.assertTrue(any("补讲（第 2 页" in t for t in texts))
        self.assertEqual(got["before"]["partial"], 1)
        self.assertEqual(got["after"]["covered"], 2)
        self.assertTrue(has_topup_file)

    def test_covered_pages_get_no_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td))

            def fake_audit(client, page, sections):
                class R:
                    def model_dump(self_inner):
                        return {"page_no": page.page_no, "status": "covered", "points": [], "missing": []}
                return R()

            with patch.object(topup.coverage_audit, "audit_page", side_effect=fake_audit), \
                 patch("tfv2.build.build_project"):
                got = topup.topup_artifact("art", artifact_path=art, client=_FakeClient())
        self.assertEqual(got["added"], 0)

    def test_missing_sections_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                topup.topup_artifact("x", artifact_path=Path(td), client=_FakeClient())
