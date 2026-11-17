"""v3 学习台：数据/质量状态/练习判分/复习/笔记/API 测试（不调模型）。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from tfv2.domain.lecture import LectureSection
from tfv2.domain.page import Page, PageImage, PageLedger, PageQuality
from tfv2.product import generate, service, store


def make_artifact(root: Path, aid: str = "unit_art", *, visual: int = 0, gate: bool = True) -> Path:
    d = root / aid
    d.mkdir(parents=True)
    (d / "lecture.html").write_text("<html><body>unit</body></html>", encoding="utf-8")
    (d / "lecture.pdf").write_bytes(b"%PDF-1.4\n")
    manifest = {
        "artifact": aid, "chapter": "单元测试讲义", "page_count": 3, "pdf_pages": 4,
        "scope_coverage": "3/3 页", "figures": 1, "sections": 1,
        "gate": {"passed": gate},
        "content_gate": {"issues": []},
        "pdf_content_gate": {"issues": []},
        "language": {"issues": []},
    }
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    sections = [{
        "id": "s1", "title": "第一节 测试", "level": 2,
        "source_refs": [{"material": "x.pdf", "page_start": 1, "page_end": 3}],
        "blocks": [{
            "id": "b1", "kind": "paragraph", "text": "这是单元测试正文。",
            "source_refs": [{"material": "x.pdf", "page_start": 1, "page_end": 3}],
        }],
    }]
    (d / "sections.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    audit = [
        {"page_no": 1, "status": "covered", "points": [{"point": "a", "covered": True}], "missing": []},
        {"page_no": 2, "status": "covered", "points": [{"point": "b", "covered": True}], "missing": []},
        {"page_no": 3, "status": "covered", "points": [{"point": "c", "covered": True}], "missing": []},
    ]
    for i in range(visual):
        audit.append({"page_no": 10 + i, "status": "visual", "points": [], "missing": []})
    (d / "coverage_audit.json").write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
    (d / "figure_report.json").write_text(json.dumps([
        {"image_id": "f1", "caption": "图", "source_pages": [1], "status": "ok", "origin": "source"}
    ], ensure_ascii=False), encoding="utf-8")
    return d


class ProductDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "artifacts"
        self.root.mkdir()
        self._old_roots = service.ARTIFACT_ROOTS
        self._old_db = store.DB_PATH
        service.ARTIFACT_ROOTS = [self.root]
        store.DB_PATH = self.base / "test.sqlite3"

    def tearDown(self) -> None:
        service.ARTIFACT_ROOTS = self._old_roots
        store.DB_PATH = self._old_db
        self.tmp.cleanup()

    def test_delivered_requires_no_visual(self) -> None:
        make_artifact(self.root, "ok", visual=0)
        item = service.list_artifacts()[0]
        self.assertEqual(item["quality"]["status"], "delivered")
        make_artifact(self.root, "vis", visual=1)
        vis = {x["id"]: x for x in service.list_artifacts()}["vis"]
        self.assertEqual(vis["quality"]["status"], "review")
        self.assertIn("visual", vis["quality"]["audit"])

    def test_gate_failure_is_rejected(self) -> None:
        make_artifact(self.root, "bad", gate=False)
        item = service.list_artifacts()[0]
        self.assertEqual(item["quality"]["status"], "rejected")

    def test_artifact_detail_sections(self) -> None:
        make_artifact(self.root, "detail")
        detail = service.get_artifact("detail")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["section_list"][0]["title"], "第一节 测试")
        self.assertEqual(detail["section_list"][0]["pages"], [1, 2, 3])

    def test_question_validation(self) -> None:
        valid = {"questions": [{
            "stem": "题干", "options": ["A", "B", "C", "D"], "answer": 0,
            "explanation": "解析", "page": 1,
        }]}
        items = service._parse_questions(valid, "a", "s", {1, 2})
        self.assertEqual(len(items), 1)
        dup = {"questions": [{
            "stem": "题干", "options": ["A", "A", "C", "D"], "answer": 0,
            "explanation": "解析", "page": 1,
        }]}
        self.assertEqual(service._parse_questions(dup, "a", "s", {1, 2}), [])
        bad_page = {"questions": [{
            "stem": "题干", "options": ["A", "B", "C", "D"], "answer": 0,
            "explanation": "解析", "page": 9,
        }]}
        self.assertEqual(service._parse_questions(bad_page, "a", "s", {1, 2}), [])

    def test_grade_mistake_review_mastery(self) -> None:
        q = {
            "id": "q1", "artifact_id": "a", "section": "s", "stem": "题干",
            "options": ["A", "B", "C", "D"], "answer": 2, "explanation": "解析", "page": 1,
        }
        store.save_questions([q])
        result = service.grade_question("q1", 0)
        self.assertFalse(result["correct"])
        self.assertIsNotNone(result["mistake_id"])
        self.assertEqual(len(store.all_mistakes()), 1)
        self.assertEqual(len(store.due_mistakes()), 1)
        updated = store.review_mistake(result["mistake_id"], True)
        self.assertEqual(updated["stage"], 1)
        mastery = store.mastery()
        self.assertEqual(mastery[0]["attempts"], 2)
        self.assertEqual(mastery[0]["accuracy"], 0.5)
        self.assertTrue(any(x["next_review"] > __import__("datetime").date.today().isoformat() for x in store.all_mistakes()))

    def test_generation_rejects_exam_and_cleans_up(self) -> None:
        from pptx import Presentation
        from pptx.util import Inches

        pdf = self.base / "exam.pptx"
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(8), Inches(2))
        box.text_frame.text = "期末考试试卷 姓名 学号 题号 得分"
        prs.save(pdf)
        old_root = generate.ARTIFACT_ROOT
        generate.ARTIFACT_ROOT = self.base / "gen_artifacts"
        try:
            with self.assertRaises(generate.GenerateError):
                generate.generate_lecture(pdf, title="试卷测试")
            leftovers = list(generate.ARTIFACT_ROOT.glob("*")) if generate.ARTIFACT_ROOT.exists() else []
            self.assertEqual(leftovers, [])
        finally:
            generate.ARTIFACT_ROOT = old_root

    def test_task_docx_export(self) -> None:
        from docx import Document
        from tfv2.render.task_docx import write_task_docx

        out = self.base / "task.docx"
        write_task_docx({"title": "任务导出", "status": "validated", "kind": "extract_points",
                         "coverage": {"pages": [1, 2], "pages_cited": [1, 2]},
                         "content": {"items": [{"point": "导数", "detail": "瞬时变化率", "page": 1}]}}, out)
        text = "\n".join(p.text for p in Document(out).paragraphs)
        self.assertIn("导数", text)
        self.assertIn("TermFinale", text)

    def test_auto_figures_picks_large_page_image(self) -> None:
        from PIL import Image

        img = self.base / "fig.png"
        Image.effect_noise((500, 400), 100).convert("RGB").save(img)
        self.assertGreater(img.stat().st_size, 15000)
        ledger = PageLedger(
            material="x", page_count=2, source_hash="h", parser_version="t",
            pages=[
                Page(material="x", page_no=1, quality=PageQuality.TEXT,
                     images=[PageImage(image_id="i1", asset_path=str(img))]),
                Page(material="x", page_no=2, quality=PageQuality.TEXT),
            ],
        )
        sec = LectureSection(id="s1", title="t")
        old = generate._vision_caption
        generate._vision_caption = lambda _path: "测试图注"
        try:
            blocks = generate._auto_figures(sec, ledger, [1, 2])
        finally:
            generate._vision_caption = old
        self.assertEqual(len(blocks), 1)
        fig = blocks[0].figure
        self.assertIn("第 1 页", fig.caption)
        self.assertIn("测试图注", fig.caption)
        self.assertTrue(fig.asset_path.startswith("assets/"))
        self.assertEqual(blocks[0].id, "s1-fig-1")

    def test_weighted_key_points_parse(self) -> None:
        self.assertEqual(generate._weighted_terms("三要素法=5、换路定则=3、戴维南"),
                         [("三要素法", 5), ("换路定则", 3), ("戴维南", 3)])

    def test_generation_constraints_are_enforced(self) -> None:
        sec = LectureSection(id="s", title="内脏神经系统", blocks=[])
        sec.blocks = []
        sec.summary = "内脏神经系统支配内脏、血管和腺体。"
        with self.assertRaises(generate.GenerateError):
            generate._check_constraints([sec], "不存在的重点", "")
        with self.assertRaises(generate.GenerateError):
            generate._check_constraints([sec], "", "内脏神经系统")
        generate._check_constraints([sec], "内脏神经系统", "")

    def test_notes(self) -> None:
        nid = store.save_note("a", "笔记正文", section="s", page=2)
        notes = store.list_notes("a")
        self.assertEqual(notes[0]["text"], "笔记正文")
        store.delete_note(nid)
        self.assertEqual(store.list_notes("a"), [])


class ProductApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "artifacts"
        self.root.mkdir()
        make_artifact(self.root, "api_art")
        self._old_roots = service.ARTIFACT_ROOTS
        self._old_db = store.DB_PATH
        service.ARTIFACT_ROOTS = [self.root]
        store.DB_PATH = self.base / "test.sqlite3"
        from tfv2.api.product_app import app
        self.client = TestClient(app)

    def tearDown(self) -> None:
        service.ARTIFACT_ROOTS = self._old_roots
        store.DB_PATH = self._old_db
        self.tmp.cleanup()

    def test_home_and_artifact_api(self) -> None:
        home = self.client.get("/api/home").json()
        self.assertEqual(len(home["artifacts"]), 1)
        art = self.client.get("/api/artifacts/api_art")
        self.assertEqual(art.status_code, 200)
        self.assertEqual(art.json()["quality"]["status"], "delivered")

    def test_manual_review_roundtrip(self) -> None:
        aid = "api_art"
        r = self.client.post(f"/api/artifacts/{aid}/review", json={"reviewer": "张老师", "notes": "例题已核对"})
        self.assertEqual(r.status_code, 200)
        detail = self.client.get(f"/api/artifacts/{aid}").json()
        self.assertEqual(detail["manual_review"]["reviewer"], "张老师")

    def test_settings_name_roundtrip(self) -> None:
        r = self.client.post("/api/settings", json={"name": "小明"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["name"], "小明")
        r = self.client.post("/api/settings", json={"name": "学习者"})
        self.assertEqual(r.json()["name"], "学习者")

    def test_notes_api(self) -> None:
        r = self.client.post("/api/notes", json={"artifact_id": "api_art", "text": "笔记", "section": "s", "page": 1})
        self.assertEqual(r.status_code, 200)
        notes = self.client.get("/api/notes?artifact_id=api_art").json()
        self.assertEqual(notes[0]["text"], "笔记")
        self.client.delete(f"/api/notes/{notes[0]['id']}")
        self.assertEqual(self.client.get("/api/notes?artifact_id=api_art").json(), [])

    def test_attempt_api_creates_mistake(self) -> None:
        store.save_questions([{
            "id": "apiq", "artifact_id": "api_art", "section": "s", "stem": "题干",
            "options": ["A", "B", "C", "D"], "answer": 1, "explanation": "解析", "page": 1,
        }])
        r = self.client.post("/api/attempts", json={"question_id": "apiq", "chosen": 0})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["correct"])
        review = self.client.get("/api/review").json()
        self.assertEqual(review["all_count"], 1)

    def test_vector_region_candidates_are_limited_and_skip_content_pages(self) -> None:
        from PIL import Image
        img = self.base / "vec.png"
        Image.new("RGB", (240, 180), "white").save(img)
        pages = []
        structure_pages = []
        for i in range(1, 16):
            pages.append(Page(material="x", page_no=i, quality=PageQuality.TEXT, text="正文" * 30))
            has_content_picture = i == 1
            structure_pages.append({
                "page": i, "width": 720, "height": 540,
                "pictures": ([{"bbox": [100, 100, 300, 250]}] if has_content_picture else
                             [{"bbox": [0, 0, 720, 540]}]) ,
                "vector_regions": [{"bbox": [50, 50, 300, 200], "asset_path": str(img)}],
            })
        ledger = PageLedger(material="x", page_count=15, source_hash="h", parser_version="t", pages=pages)
        generate._add_structure_vector_figures(ledger, {"pages": structure_pages})
        vectors = [i for p in ledger.pages for i in p.images if i.image_id.startswith("vector_")]
        self.assertLessEqual(len(vectors), 12)
        self.assertFalse(any(i.image_id.startswith("vector_") for i in ledger.pages[0].images))

    def test_section_meta_fallback_fills_missing_fields(self) -> None:
        sec = LectureSection(id="s1", title="三极管电流关系", blocks=[])
        generate._fallback_section_meta([sec], "zh")
        self.assertTrue(sec.objectives)
        self.assertTrue(sec.key_terms)
        self.assertTrue(sec.self_test)

    def test_scope_page_refs_are_clamped(self) -> None:
        sec = LectureSection(id="s1", title="范围",
                             source_refs=[{"material": "x", "page_start": 23, "page_end": 23}])
        generate._clamp_page_refs([sec], 10)
        self.assertEqual(sec.source_refs[0].page_start, 10)
        self.assertEqual(sec.source_refs[0].page_end, 10)

    def test_index_and_missing_artifact(self) -> None:
        index = self.client.get("/")
        self.assertEqual(index.status_code, 200)
        self.assertIn("TermFinale", index.text)
        self.assertEqual(self.client.get("/api/artifacts/nope").status_code, 404)


if __name__ == "__main__":
    unittest.main()
