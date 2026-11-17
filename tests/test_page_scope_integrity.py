"""页码完整性：选了多少页就必须做多少页，不能静默截断。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from tfv2.product import source_digest


def _artifact(root: Path, pages: int) -> Path:
    art = root / "art"
    (art / "source").mkdir(parents=True)
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((60, 80), f"page {i + 1} text for scope integrity check", fontsize=12)
    doc.save(str(art / "source" / "src.pdf"))
    doc.close()
    rows = [{"page": i, "text": f"第{i}页正文内容，用于页码完整性测试。" * 3} for i in range(1, pages + 1)]
    (art / "source_pages.json").write_text(
        json.dumps({"version": 1, "page_count": pages, "pages": rows}, ensure_ascii=False), encoding="utf-8")
    (art / "sections.json").write_text("[]", encoding="utf-8")
    (art / "project.json").write_text(json.dumps({
        "id": "art", "chapter_title": "t",
        "header": {"title": "t", "course": "t"}, "summary": {"overview": "o"},
        "closing": {"persona": "老师", "text": "c"},
        "footer": {"coverage_percent": 100, "material_label": "m"},
        "sections_files": ["sections.json"], "page_count": pages, "coverage_percent": 100,
        "scope_pages": list(range(1, pages + 1)), "out_dir": ".",
        "source_file": "source/src.pdf", "assets_dir": "source_assets",
    }, ensure_ascii=False), encoding="utf-8")
    return art


class ScopeIntegrityTests(unittest.TestCase):
    def test_超出资料页码直接报错(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            art = _artifact(root, 3)
            with patch.object(source_digest.service, "artifact_path", return_value=art):
                with self.assertRaises(ValueError) as ctx:
                    source_digest.build_source_digest("art", [1, 2, 99], "out")
            self.assertIn("超出资料范围", str(ctx.exception))
            self.assertIn("99", str(ctx.exception))

    def test_没有有效页码时报错(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            art = _artifact(root, 3)
            with patch.object(source_digest.service, "artifact_path", return_value=art):
                with self.assertRaises(ValueError):
                    source_digest.build_source_digest("art", [], "out")

    def test_manifest_记录实际构建页数而不是请求页数(self) -> None:
        source = Path("tfv2/api/product_app.py").read_text(encoding="utf-8")
        segment = source.split("def artifact_generate_selected")[1].split("@app.post")[0]
        self.assertIn("requested_page_count", segment)
        self.assertIn("built_count", segment)
        self.assertNotIn('"page_count": len(pages)', segment)


if __name__ == "__main__":
    unittest.main()


class OcrPageLectureTests(unittest.TestCase):
    """OCR 补出的页文字默认只进检索；讲义仍用原页影像，不把 OCR 当正文。"""

    def test_ocr_pages_render_as_images(self) -> None:
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from tfv2.product.sources import _patch_source_pages_with_ocr

        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            (out / "source_pages.json").write_text(json.dumps({
                "version": 1, "page_count": 2,
                "pages": [{"page": 1, "text": "", "quality": "image_only"},
                          {"page": 2, "text": "已有文字", "quality": "text"}],
            }, ensure_ascii=False), encoding="utf-8")
            patched = _patch_source_pages_with_ocr(out, [{"start": 1, "count": 2,
                                                          "pages": {1: "OCR 文字一", 2: "OCR 文字二"}}])
            self.assertEqual(patched, 1)
            rows = json.loads((out / "source_pages.json").read_text(encoding="utf-8"))["pages"]
            self.assertEqual(rows[0]["text"], "OCR 文字一")
            self.assertTrue(rows[0]["ocr_used"])
            self.assertEqual(rows[1]["text"], "已有文字", "有文字的页不能被 OCR 覆盖")


class TextModeTests(unittest.TestCase):
    """扫描件默认影像；只有显式开“文字版”才用 OCR 文字排版。"""

    def test_decisions(self) -> None:
        from tfv2.product.source_digest import page_should_be_image as F
        long_text = "这一页有足够长的正文内容，可以被当作文字页处理。" * 2
        self.assertTrue(F(long_text, "text", ocr_used=True), "OCR 页默认仍用影像")
        self.assertFalse(F(long_text, "text", ocr_used=True, text_from_ocr=True), "文字版要用文字")
        self.assertTrue(F(long_text, "text", scan_mode=True, text_from_ocr=True), "影像版始终影像")
        self.assertTrue(F("短", "text"), "短文本按影像页")
        # 公式型 OCR 文本（考场真题就是这种）在文字版下也要排文字
        self.assertFalse(F("∃x∈(a,b), f(x)>0 且极限存在，求参数范围。", "formula",
                           ocr_used=True, text_from_ocr=True))
        self.assertTrue(F("∃x∈(a,b), f(x)>0 且极限存在，求参数范围。", "formula", ocr_used=True))
        self.assertFalse(F(long_text, "text"), "正常文字页用文字")

    def test_api_payload_accepts_text_mode(self) -> None:
        from tfv2.api.product_app import SelectedPreviewPayload
        self.assertFalse(SelectedPreviewPayload(pages=[1]).text_mode)
        self.assertTrue(SelectedPreviewPayload(pages=[1], text_mode=True).text_mode)

    def test_generate_selected_passes_text_mode(self) -> None:
        from pathlib import Path
        segment = Path("tfv2/api/product_app.py").read_text(encoding="utf-8")
        segment = segment.split("def artifact_generate_selected")[1].split("@app.post")[0]
        self.assertIn("text_from_ocr=payload.text_mode", segment)
        self.assertIn("payload.text_mode", segment.split("use_digest =")[1][:200])


class DuplicatePageTests(unittest.TestCase):
    """重复页只展开一次：判定是纯函数，短文本不算重复。"""

    def test_duplicate_detected_and_registered(self) -> None:
        from tfv2.product.source_digest import duplicate_page_of, register_page_text
        seen: dict[str, int] = {}
        body = "放大电路的静态工作点需要先画直流通路，再列方程求解。" * 2
        register_page_text(body, seen, 3)
        self.assertIsNone(duplicate_page_of("另一段完全不同的正文" * 3, seen))
        self.assertEqual(duplicate_page_of(body, seen), 3)
        # 空白差异不影响判定
        self.assertEqual(duplicate_page_of(body.replace("，", "， "), seen), 3)

    def test_short_text_never_duplicate(self) -> None:
        from tfv2.product.source_digest import duplicate_page_of, register_page_text
        seen: dict[str, int] = {}
        register_page_text("短句", seen, 1)
        self.assertIsNone(duplicate_page_of("短句", seen))

    def test_first_registration_wins(self) -> None:
        from tfv2.product.source_digest import duplicate_page_of, register_page_text
        seen: dict[str, int] = {}
        body = "三极管的电流放大系数体现放大能力，β 过大时稳定性变差。" * 2
        register_page_text(body, seen, 1)
        register_page_text(body, seen, 5)
        self.assertEqual(duplicate_page_of(body, seen), 1)


class MaterialLabelTests(unittest.TestCase):
    """讲义标题不能出现 gen_2026... 这种产物 id。"""

    def test_manifest_title_beats_artifact_id(self) -> None:
        from tfv2.product.source_digest import material_label
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "manifest.json").write_text(json.dumps({"title": "模拟电子技术 第1–60页（精品）"}),
                                                encoding="utf-8")
            self.assertEqual(material_label(root, "gen_20261115_123905_f21786"), "模拟电子技术（精品）")

    def test_project_title_used_when_manifest_missing(self) -> None:
        from tfv2.product.source_digest import material_label
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "project.json").write_text(json.dumps({"header": {"title": "高数 第3–8页"}}),
                                               encoding="utf-8")
            self.assertEqual(material_label(root, "sel_123abc"), "高数")

    def test_artifact_id_never_leaks(self) -> None:
        from tfv2.product.source_digest import material_label
        with tempfile.TemporaryDirectory() as td:
            got = material_label(Path(td), "gen_20261117_075523_b380d7")
        self.assertEqual(got, "资料")


class ParagraphDedupeTests(unittest.TestCase):
    """长材料跨节重复段落：只保留一处，出处仍可回看。"""

    def test_key_and_duplicate(self) -> None:
        from tfv2.product.source_digest import (duplicate_paragraph_of, paragraph_key,
                                               register_paragraph)
        seen: dict[str, int] = {}
        body = "放大电路的静态工作点需要先画直流通路，再列输入回路与输出回路方程求解。" * 2
        self.assertTrue(paragraph_key(body))
        register_paragraph(body, seen, 2)
        self.assertEqual(duplicate_paragraph_of(body, seen), 2)
        self.assertIsNone(duplicate_paragraph_of(body, {}))
        self.assertEqual(paragraph_key("短句"), "", "太短的段落不参与去重")

    def test_whitespace_insensitive(self) -> None:
        from tfv2.product.source_digest import duplicate_paragraph_of, register_paragraph
        seen: dict[str, int] = {}
        body = "三极管的电流放大系数体现放大能力，β 过大时稳定性变差。" * 3
        register_paragraph(body, seen, 1)
        self.assertEqual(duplicate_paragraph_of(body.replace("，", "， "), seen), 1)
