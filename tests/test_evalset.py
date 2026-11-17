"""评测样本清单：加样本只改 evalset.json，结构必须稳定。"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALSET = ROOT / "evalset.json"


class EvalSetTests(unittest.TestCase):
    def test_file_exists_and_parses(self) -> None:
        self.assertTrue(EVALSET.is_file(), "缺少 evalset.json")
        data = json.loads(EVALSET.read_text(encoding="utf-8"))
        for key in ("lectures", "parses", "references"):
            self.assertIsInstance(data.get(key), list, key)
            self.assertTrue(data[key], f"{key} 不能为空")

    def test_case_schema(self) -> None:
        data = json.loads(EVALSET.read_text(encoding="utf-8"))
        ids = []
        for case in data["lectures"]:
            self.assertTrue(case.get("id"), "lectures 需要 id")
            ids.append(case["id"])
        self.assertEqual(len(ids), len(set(ids)), "lectures id 不能重复")
        for case in data["parses"] + data["references"]:
            self.assertTrue(str(case.get("path") or "").endswith(".pdf"),
                            f"{case} 需要 .pdf 路径")

    def test_reference_subset_of_parses(self) -> None:
        data = json.loads(EVALSET.read_text(encoding="utf-8"))
        parse_paths = {c["path"] for c in data["parses"]}
        ref_paths = {c["path"] for c in data["references"]}
        self.assertTrue(ref_paths.issubset(parse_paths),
                        "references 用的真题也应出现在 parses 里")


if __name__ == "__main__":
    unittest.main()
