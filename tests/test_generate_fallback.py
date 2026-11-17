"""生成不能老是失败：模型成文挂了，也要交一份“按原文页组织”的讲义。"""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from fastapi.testclient import TestClient

from tfv2.api import product_app
from tfv2.api.product_app import app as product_app_instance


def _stub_digest(aid, pages, art_id, **kwargs):
    """替代真正的 digest：写出 handler 需要的四个文件。"""
    from tfv2.product import generate

    dest = Path(generate.ARTIFACT_ROOT) / art_id
    dest.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    doc.new_page()
    doc.save(str(dest / "lecture.pdf"))
    doc.close()
    (dest / "sections.json").write_text(json.dumps(
        [{"id": "s1", "title": "第 1 页", "blocks": [], "source_refs": [{"page_start": 1, "page_end": 1}]}],
        ensure_ascii=False), encoding="utf-8")
    (dest / "source_pages.json").write_text(json.dumps(
        {"page_count": len(pages), "pages": [{"page": i + 1, "text": "资料正文" * 10} for i in range(len(pages))]},
        ensure_ascii=False), encoding="utf-8")
    (dest / "manifest.json").write_text(json.dumps({"page_count": len(pages)}, ensure_ascii=False), encoding="utf-8")
    for hook in (kwargs.get("progress"),):
        if callable(hook):
            hook(100, "完成")


class GenerateFallbackTests(unittest.TestCase):
    def test_preview_failure_falls_back_to_digest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            art = root / "art"
            art.mkdir()
            jobs: dict[str, list[dict]] = {}

            def update_job(job_id, **kw):
                jobs.setdefault(job_id, []).append(dict(kw))

            with patch.object(product_app.service, "artifact_path", return_value=art), \
                 patch.object(product_app.service, "get_artifact", return_value={}), \
                 patch.object(product_app.service, "get_course", return_value=None), \
                 patch.object(product_app.store, "create_job", side_effect=lambda jid, kind, payload=None: None), \
                 patch.object(product_app.store, "update_job", side_effect=update_job), \
                 patch("tfv2.product.generate.ARTIFACT_ROOT", root / "artifacts"), \
                 patch("tfv2.product.preview_generate.generate_preview",
                       side_effect=RuntimeError("模型超时")), \
                 patch("tfv2.product.source_digest.build_source_digest", side_effect=_stub_digest):
                client = TestClient(product_app_instance)
                resp = client.post("/api/artifacts/art/generate-selected",
                                   json={"pages": [1, 2], "tier": ""})
                self.assertEqual(resp.status_code, 200, resp.text)
                job_id = resp.json()["job_id"]
                dest = root / "artifacts" / ("sel-" + job_id)
                deadline = time.time() + 10
                while time.time() < deadline and not (dest / "manifest.json").is_file():
                    time.sleep(0.05)
                self.assertTrue((dest / "manifest.json").is_file(), "失败后没有交付物")
                manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("fallback_reason", manifest)
            self.assertIn("按资料原页组织", manifest["fallback_reason"])
            self.assertIn("模型超时", manifest["fallback_reason"])
            steps = [str(item.get("step") or "") for history in jobs.values() for item in history]
            self.assertTrue(any("模型成文没成功" in step for step in steps), steps)


class JobResumableFlagTests(unittest.TestCase):
    def test_resumable_only_with_checkpoint_and_failed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "lecture_checkpoints").mkdir()
            (root / "exam_checkpoints").mkdir()
            (root / "lecture_checkpoints" / "abc.json").write_text("{}", encoding="utf-8")
            with patch("tfv2.product.generate.UPLOAD_ROOT", root):
                self.assertTrue(product_app._job_resumable({"id": "abc", "kind": "lecture"}))
                self.assertFalse(product_app._job_resumable({"id": "nope", "kind": "lecture"}))
                self.assertFalse(product_app._job_resumable({"id": "abc", "kind": "exam"}))
                self.assertFalse(product_app._job_resumable({"id": "abc", "kind": "other"}))
