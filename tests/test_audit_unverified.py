"""复核失败 ≠ 内容缺失：不能因为超时把好讲义判成“未通过”。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from tfv2.quality import artifact_audit
from tfv2.product import service


def _artifact(root: Path) -> Path:
    art = root / "art"
    art.mkdir()
    doc = pymupdf.open()
    doc.new_page()
    doc.save(str(art / "lecture.pdf"))
    doc.close()
    (art / "lecture.html").write_text("<html>讲义</html>", encoding="utf-8")
    (art / "source_pages.json").write_text(json.dumps({
        "material": "m", "pages": [{"page": 1, "text": "正文" * 30}]
    }, ensure_ascii=False), encoding="utf-8")
    (art / "sections.json").write_text(json.dumps([{
        "id": "s1", "title": "章",
        "blocks": [{"id": "b1", "kind": "paragraph", "text": "正文",
                    "source_refs": [{"material": "m", "page_start": 1, "page_end": 1}]}],
        "source_refs": [{"material": "m", "page_start": 1, "page_end": 1}],
    }], ensure_ascii=False), encoding="utf-8")
    (art / "manifest.json").write_text(json.dumps({"gate": {"passed": True}, "content_gate": {},
                                                   "pdf_content_gate": {}, "language": {}}),
                                       encoding="utf-8")
    return art


class AuditUnverifiedTests(unittest.TestCase):
    def test_audit_exception_marks_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td))
            with patch.object(artifact_audit, "audit_page", side_effect=TimeoutError("timed out")):
                rows = artifact_audit.audit_artifact_dir(art)
        self.assertEqual(rows[0]["status"], "unverified")
        self.assertIn("复核没跑完", rows[0]["note"])

    def test_unverified_does_not_fail_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td))
            (art / "coverage_audit.json").write_text(json.dumps([
                {"page_no": 1, "status": "unverified", "points": [], "missing": []}
            ]), encoding="utf-8")
            with patch.object(service, "artifact_path", return_value=art):
                service.refresh_artifact_gate("aid")
            man = json.loads((art / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(man["gate"]["passed"], "复核没跑完不该判内容未通过")
        self.assertEqual(man["coverage_audit"]["unverified"], 1)

    def test_partial_kept_out_of_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td))
            (art / "coverage_audit.json").write_text(json.dumps([
                {"page_no": 1, "status": "partial", "points": [], "missing": ["x"]}
            ]), encoding="utf-8")
            with patch.object(service, "artifact_path", return_value=art):
                service.refresh_artifact_gate("aid")
            man = json.loads((art / "manifest.json").read_text(encoding="utf-8"))
        # partial 记在 coverage_audit 里，让状态变“待复核”；不篡改结构门禁
        self.assertTrue(man["gate"]["passed"])
        self.assertEqual(man["coverage_audit"]["partial"], 1)


class AuditClientFallbackTests(unittest.TestCase):
    """Qwen JSON 坏了要换 DeepSeek 再试，而不是直接判内容缺失。"""

    def test_falls_back_to_second_client(self) -> None:
        calls = []

        def fake_audit(client, page, sections, overview=False):
            calls.append(client)
            if len(calls) == 1:
                raise RuntimeError("Qwen JSON 解析失败")
            from tfv2.quality.coverage_audit import PageCoverage
            return PageCoverage(page_no=page.page_no, status="covered", points=[], missing=[])

        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td))
            with patch.object(artifact_audit, "QwenTextClient", return_value="qwen"), \
                 patch("tfv2.llm.kimi.KimiClient", side_effect=RuntimeError("no kimi")), \
                 patch("tfv2.llm.client.DeepSeekClient", return_value="deepseek"), \
                 patch.object(artifact_audit, "audit_page", side_effect=fake_audit):
                rows = artifact_audit.audit_artifact_dir(art)
        self.assertEqual(rows[0]["status"], "covered")
        self.assertEqual(calls[0], "qwen")
        self.assertEqual(calls[1], "deepseek")


class CoverageAuditEmptyTests(unittest.TestCase):
    """有正文但复核没返回知识点，不能当成“内容为空”。"""

    def _page(self, text: str):
        from tfv2.domain.page import Page, PageQuality
        return Page(material="m", page_no=1, text=text, quality=PageQuality.TEXT)

    def _sections(self):
        from tfv2.domain.lecture import LectureSection
        return [LectureSection(id="s1", title="章", blocks=[{
            "id": "b1", "kind": "paragraph", "text": "放大电路的静态工作点。",
            "source_refs": [{"material": "m", "page_start": 1, "page_end": 1}]}],
            source_refs=[{"material": "m", "page_start": 1, "page_end": 1}])]

    def test_long_text_without_points_is_unverified(self) -> None:
        from tfv2.quality.coverage_audit import audit_page

        class Client:
            def json(self, *a, **k):
                return {}

        page = self._page("这一页有完整的正文内容，讲的是放大电路的工作原理与静态工作点。" * 3)
        got = audit_page(Client(), page, self._sections())
        self.assertEqual(got.status, "unverified")

    def test_short_text_stays_empty(self) -> None:
        from tfv2.quality.coverage_audit import audit_page

        class Client:
            def json(self, *a, **k):
                return {}

        got = audit_page(Client(), self._page("目录"), self._sections())
        self.assertEqual(got.status, "empty")
