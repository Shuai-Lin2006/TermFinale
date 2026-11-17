"""产物质量指标接口：本地计算、可缓存、影像版单独报。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from tfv2.api import product_app


def _artifact(root: Path, *, pages=3, figure_pages=0, tier: str = "") -> Path:
    art = root / "art"
    (art / "source_assets").mkdir(parents=True)
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((60, 80), f"第{i+1}页 放大电路静态工作点", fontsize=12)
    doc.save(str(art / "lecture.pdf")); doc.close()
    rows = []
    for i in range(pages):
        rows.append({"page": i + 1, "text": "放大电路的静态工作点需要先画直流通路，再列方程求解。" * 2})
    (art / "source_pages.json").write_text(json.dumps({"page_count": pages, "pages": rows},
                                                      ensure_ascii=False), encoding="utf-8")
    blocks = [{"id": "b1", "kind": "paragraph",
               "text": "放大电路的静态工作点需要先画直流通路，再列方程求解。",
               "source_refs": [{"page_start": 1, "page_end": 1}]}]
    for i in range(figure_pages):
        blocks.append({"id": f"f{i}", "kind": "figure", "text": "",
                       "source_refs": [{"page_start": i + 1, "page_end": i + 1}]})
    (art / "sections.json").write_text(json.dumps([{"id": "s1", "title": "章", "blocks": blocks,
                                                    "source_refs": [{"page_start": 1, "page_end": pages}]}],
                                                  ensure_ascii=False), encoding="utf-8")
    (art / "manifest.json").write_text(json.dumps({"page_count": pages, "tier": tier},
                                                  ensure_ascii=False), encoding="utf-8")
    return art


class ArtifactMetricsTests(unittest.TestCase):
    def test_text_artifact_returns_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td))
            with patch.object(product_app.service, "artifact_path", return_value=art):
                got = product_app.artifact_metrics("aid")
        self.assertFalse(got["image_mode"])
        self.assertEqual(got["page_count"], 3)
        self.assertIn("citation_support", got)
        self.assertIn("term_recall", got)
        self.assertIn("dup_sentence", got)
        self.assertGreaterEqual(got["citation_support"], 0.5)

    def test_image_artifact_reports_images_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td), pages=2, figure_pages=2)
            for i in range(2):
                (art / "source_assets" / f"p{i}.png").write_bytes(b"x")
            with patch.object(product_app.service, "artifact_path", return_value=art):
                got = product_app.artifact_metrics("aid")
        self.assertTrue(got["image_mode"])
        self.assertEqual(got["images"], 2)
        self.assertNotIn("citation_support", got)

    def test_result_is_cached(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td))
            with patch.object(product_app.service, "artifact_path", return_value=art):
                first = product_app.artifact_metrics("aid")
                self.assertTrue((art / "metrics.json").is_file())
                second = product_app.artifact_metrics("aid")
        self.assertEqual(first["citation_support"], second["citation_support"])

    def test_coverage_target_from_tier(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td), pages=60, tier="premium")
            with patch.object(product_app.service, "artifact_path", return_value=art):
                got = product_app.artifact_metrics("aid")
        self.assertEqual(got["coverage_target"], 70)
        self.assertTrue(got["coverage_met"])
        self.assertAlmostEqual(got["coverage_percent"], 100.0)

    def test_coverage_not_met_when_short(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td), pages=200, tier="broad")
            # 只引用第 1 页 → 覆盖 0.5%，远低于 75%
            sec = json.loads((art / "sections.json").read_text(encoding="utf-8"))
            sec[0]["source_refs"] = [{"page_start": 1, "page_end": 1}]
            (art / "sections.json").write_text(json.dumps(sec), encoding="utf-8")
            with patch.object(product_app.service, "artifact_path", return_value=art):
                got = product_app.artifact_metrics("aid")
        self.assertEqual(got["coverage_target"], 75)
        self.assertFalse(got["coverage_met"])

    def test_missing_artifact_404(self) -> None:
        from fastapi import HTTPException
        with patch.object(product_app.service, "artifact_path", return_value=None):
            with self.assertRaises(HTTPException):
                product_app.artifact_metrics("none")


class FallbackSectionsTests(unittest.TestCase):
    def test_fallback_sections_surface_in_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            art = _artifact(Path(td), pages=2)
            (art / "project.json").write_text(json.dumps({
                "fallback_sections": [{"index": 2, "label": "第 2 节", "pages": [2], "reason": "模型超时"}],
                "page_fill_pages": 1,
            }, ensure_ascii=False), encoding="utf-8")
            with patch.object(product_app.service, "artifact_path", return_value=art):
                got = product_app.artifact_metrics("aid")
        self.assertEqual(got["fallback_count"], 1)
        self.assertEqual(got["fallback_sections"][0]["label"], "第 2 节")
        self.assertEqual(got["page_fill_pages"], 1)
        self.assertAlmostEqual(got["page_fill_ratio"], 0.5)
