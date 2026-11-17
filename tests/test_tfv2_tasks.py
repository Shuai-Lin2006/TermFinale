"""v3 四类任务：页码/选项/答案审计门禁（Fake 模型，不联网）。"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tfv2.product import service, tasks


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)

    def json(self, system, user, *, max_tokens=4096, temperature=0.35):
        if not self.responses:
            raise RuntimeError("no fake response")
        return self.responses.pop(0)


def artifact(root: Path, aid: str = "task_art") -> Path:
    d = root / aid
    d.mkdir(parents=True)
    (d / "manifest.json").write_text('{"chapter":"任务测试","gate":{"passed":true}}', encoding="utf-8")
    (d / "lecture.html").write_text("<html></html>", encoding="utf-8")
    sections = [{
        "id": "s1", "title": "第一节", "source_refs": [{"material": "x", "page_start": 1, "page_end": 2}],
        "blocks": [
            {"id": "b1", "kind": "paragraph", "text": "导数表示瞬时变化率。",
             "source_refs": [{"material": "x", "page_start": 1, "page_end": 1}]},
            {"id": "b2", "kind": "paragraph", "text": "可导必连续，连续不一定可导。",
             "source_refs": [{"material": "x", "page_start": 2, "page_end": 2}]},
        ],
    }]
    (d / "sections.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    return d


class TaskTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["TFV2_TASK_CACHE"] = "0"
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "artifacts"
        self.root.mkdir()
        self._old = service.ARTIFACT_ROOTS
        service.ARTIFACT_ROOTS = [self.root]
        artifact(self.root)

    def tearDown(self) -> None:
        service.ARTIFACT_ROOTS = self._old
        self.tmp.cleanup()

    def test_points_validated_and_bad_page_rejected(self) -> None:
        good = {"items": [{"point": "导数定义", "detail": "瞬时变化率", "page": 1},
                          {"point": "可导与连续", "detail": "可导必连续", "page": 2}]}
        doc = tasks.run_task("extract_points", "task_art", "s1", client=FakeClient(good))
        self.assertEqual(doc["status"], "validated")
        self.assertEqual(doc["coverage"]["coverage"], 1.0)
        bad = {"items": [{"point": "x", "detail": "", "page": 9}]}
        doc = tasks.run_task("extract_points", "task_art", "s1", client=FakeClient(bad))
        self.assertEqual(doc["status"], "rejected")

    def test_nouns_duplicate_definition_rejected(self) -> None:
        bad = {"items": [{"term": "导数", "definition": "", "page": 1}]}
        doc = tasks.run_task("extract_nouns", "task_art", "s1", client=FakeClient(bad))
        self.assertEqual(doc["status"], "rejected")

    def test_questions_duplicate_options_rejected(self) -> None:
        bad = {"items": [{"no": "1", "stem": "导数表示什么？", "options": ["A", "A", "C", "D"],
                          "answer": 0, "analysis": "x", "source_page": 1, "source_no": "1"}]}
        doc = tasks.run_task("extract_questions", "task_art", "s1", client=FakeClient(bad))
        self.assertEqual(doc["status"], "rejected")

    def test_calculation_question_is_allowed(self) -> None:
        data = {"items": [
            {"no": "1", "qtype": "calculation", "stem": "导数表示瞬时变化率。", "options": [],
             "answer_text": "f'(x)=2x", "analysis": "按定义求导", "source_page": 1, "source_no": "1"},
            {"no": "2", "qtype": "short_answer", "stem": "可导必连续。", "options": [],
             "answer_text": "因为可导定义推出连续", "analysis": "按定义", "source_page": 2, "source_no": "2"},
        ]}
        doc = tasks.run_task("extract_questions", "task_art", "s1", client=FakeClient(data))
        self.assertEqual(doc["status"], "validated")
        self.assertEqual(doc["content"]["items"][0]["qtype"], "calculation")
        self.assertEqual(doc["content"]["items"][1]["qtype"], "short_answer")
        self.assertEqual(doc["content"]["items"][0]["answer_text"], "f'(x)=2x")

    def test_paper_calculation_manual_audit(self) -> None:
        paper = {"title": "混合卷", "questions": [{
            "no": "1", "qtype": "calculation", "stem": "求导。", "options": [],
            "answer_text": "2x", "analysis": "解析", "source_page": 1,
            "source_no": "1", "provenance": "",
        }]}
        doc = tasks.run_task("paper", "task_art", "s1", mode="mock", client=FakeClient(paper))
        self.assertEqual(doc["status"], "validated")
        self.assertTrue(doc["content"]["answer_audit"]["manual"])
        self.assertEqual(doc["content"]["questions"][0]["answer"], None)

    def test_paper_audit_conflict_rejected(self) -> None:
        paper = {"title": "小卷", "questions": [{
            "no": "1", "stem": "导数表示什么？", "options": ["A", "B", "C", "D"],
            "answer": 0, "analysis": "解析", "source_page": 1, "source_no": "1", "provenance": "",
        }]}
        doc = tasks.run_task("paper", "task_art", "s1", mode="mock",
                             client=FakeClient(paper, {"answers": [1]}))
        self.assertEqual(doc["status"], "rejected")
        self.assertIn("答案审计冲突", " ".join(doc["issues"]))

    def test_paper_audit_agrees_validated(self) -> None:
        paper = {"title": "小卷", "questions": [{
            "no": "1", "stem": "导数表示什么？", "options": ["A", "B", "C", "D"],
            "answer": 0, "analysis": "解析", "source_page": 1, "source_no": "1", "provenance": "",
        }]}
        doc = tasks.run_task("paper", "task_art", "s1", mode="mock",
                             client=FakeClient(paper, {"answers": [0]}))
        self.assertEqual(doc["status"], "validated")

    def test_analysis_empty_rejected(self) -> None:
        doc = tasks.run_task("analysis", "task_art", "s1", client=FakeClient({"one_line": ""}))
        self.assertEqual(doc["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
