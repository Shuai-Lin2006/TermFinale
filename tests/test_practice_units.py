"""练习按资料页出题：公式/图片页显式跳过，页码不越界。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tfv2.product import service


class FakeClient:
    def __init__(self, questions):
        self.questions = questions
        self.prompts = []

    def json(self, system, user, **kwargs):
        self.prompts.append(user)
        return {"questions": self.questions}


def _q(page: int, n: int = 1) -> dict:
    return {"stem": f"第{n}题：三极管工作在放大区时基极电流与集电极电流的关系是",
            "options": ["甲", "乙", "丙", "丁"], "answer": 0,
            "explanation": "按 β 的定义推导即可", "page": page}


class PracticeUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.dir = Path(self._td.name)
        rows = [
            {"page": 1, "text": "共射放大电路的静态工作点计算需要直流通路。" * 6},
            {"page": 2, "text": "\ufffd\ue000 公式影像页"},
            {"page": 3, "text": "三极管的电流放大系数决定放大能力，共射接法常用于放大电路。" * 6},
        ]
        (self.dir / "source_pages.json").write_text(
            json.dumps({"version": 1, "page_count": 3, "pages": rows}, ensure_ascii=False),
            encoding="utf-8")
        self.patch = patch.object(service, "_artifact_dir", return_value=self.dir)
        self.patch.start()

    def tearDown(self) -> None:
        self.patch.stop()
        self._td.cleanup()

    def test_formula_page_is_skipped_and_reported(self) -> None:
        client = FakeClient([_q(1), _q(3, 2)])
        with patch.object(service.store, "save_questions", return_value=None):
            got = service.practice_from_units("aid", [1, 2, 3], count=2, client=client)
        self.assertEqual(got["skipped_pages"], [2])
        self.assertEqual(got["used_pages"], [1, 3])
        self.assertEqual(len(got["questions"]), 2)
        # 公式页不该进 prompt
        self.assertNotIn("公式影像页", client.prompts[0])

    def test_all_formula_pages_raise(self) -> None:
        with self.assertRaises(service.PracticeError):
            service.practice_from_units("aid", [2], count=1, client=FakeClient([]))

    def test_page_out_of_range_rejected(self) -> None:
        with self.assertRaises(service.PracticeError):
            service.practice_from_units("aid", [1, 99], count=1, client=FakeClient([_q(1)]))

    def test_legacy_function_returns_question_list(self) -> None:
        with patch.object(service, "practice_from_units",
                          return_value={"questions": [_q(1)], "skipped_pages": [2],
                                        "used_pages": [1]}):
            items = service.generate_questions_from_pages("aid", [1], count=1)
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 1)
        self.assertIn("stem", items[0])


if __name__ == "__main__":
    unittest.main()
