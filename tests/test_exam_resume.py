
"""Round 2: exam resume skips completed sections and keeps their questions."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tfv2.product import exam, service
from tfv2.product import store


class FakeClient:
    def __init__(self):
        self.calls = []

    def json(self, system, user, **kwargs):
        self.calls.append((system, user))
        if "独立解题人" in system:
            count = max(1, user.count("\n\n") + 1)
            return {"answers": [0] * count}
        return {"title": "续跑卷", "sections": []}


def make_artifact(root: Path, aid: str) -> Path:
    d = root / aid; d.mkdir(parents=True)
    (d / "lecture.html").write_text("<html></html>", encoding="utf-8")
    (d / "manifest.json").write_text(json.dumps({"artifact": aid, "chapter": "续跑"}), encoding="utf-8")
    (d / "sections.json").write_text(json.dumps([{
        "id": "s1", "title": "第一节", "source_refs": [
            {"material": "x", "page_start": 1, "page_end": 3}],
        "blocks": [{"id": "b1", "kind": "paragraph", "text": "内容",
                    "source_refs": [{"material": "x", "page_start": 1, "page_end": 3}]}],
    }]), encoding="utf-8")
    return d


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.aid = "resume_art"
        make_artifact(self.root, self.aid)
        self.old_roots = service.ARTIFACT_ROOTS
        service.ARTIFACT_ROOTS = [self.root]
        self.old_db = store.DB_PATH
        store.DB_PATH = self.root / "db.sqlite3"

    def tearDown(self):
        service.ARTIFACT_ROOTS = self.old_roots
        store.DB_PATH = self.old_db
        self.tmp.cleanup()

    def test_checkpoint_questions_are_not_regenerated(self):
        qs = [{
            "qtype": "choice", "stem": ["神经传导的临床病例分析","突触传递过程涉及哪些结构","反射弧由哪几部分组成"][i],
            "options": ["A", "B", "C", "D"], "answer": 0, "answer_text": "A",
            "analysis": "A 正确。", "source_page": i + 1, "source_no": str(i + 1),
            "score": 33.4 if i == 2 else 33.3,
        } for i in range(3)]
        checkpoint = {
            "title": "续跑卷",
            "sections": [{"name": "一、选择题", "type": "choice", "count": 3,
                          "score": 100, "questions": qs}],
        }
        fake = FakeClient()
        doc = exam.run_exam(
            self.aid, mode="mock", subject="医学", difficulty=3, types="choice",
            client=fake, checkpoint=checkpoint,
            checkpoint_path=self.root / "checkpoint.json",
        )
        self.assertEqual(len([q for s in doc["content"]["sections"] for q in s["questions"]]), 3)
        self.assertEqual(doc["status"], "validated")
        self.assertEqual(doc["content"]["sections"][0]["questions"][0]["stem"], "神经传导的临床病例分析")
        self.assertTrue((self.root / "checkpoint.json").is_file())


if __name__ == "__main__":
    unittest.main()
