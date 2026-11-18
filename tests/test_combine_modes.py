"""拼接三种组合方式的路由：fuse / append / 不拼接。

只验证路由和返回值结构；真实产物由 scripts/fusion_e2e.py 验收。
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tfv2.product.combine import combine_materials

MATERIALS = [{"artifact_id": "a", "pages": [1, 2]},
             {"artifact_id": "b", "pages": [3]}]


class CombineModeTests(unittest.TestCase):
    def test_separate_makes_one_artifact_per_material(self) -> None:
        with patch("tfv2.product.combine.build_source_digest") as digest:
            result = combine_materials("out", MATERIALS, merge=False)
        self.assertFalse(result["merge"])
        self.assertEqual(result["mode"], "separate")
        self.assertEqual(result["artifacts"], ["out-m1", "out-m2"])
        self.assertEqual(digest.call_count, 2)

    def test_append_still_uses_book_merge_and_labels_itself(self) -> None:
        with patch("tfv2.product.combine.build_source_digest"), \
                patch("tfv2.product.combine.merge_chunks", return_value=Path("/tmp/x.pdf")) as merge, \
                patch("tfv2.product.combine.service.artifact_path", return_value=None):
            result = combine_materials("out", MATERIALS, merge=True, mode="append")
        self.assertEqual(result["mode"], "append")
        self.assertEqual(Path(result["pdf"]), Path("/tmp/x.pdf"))
        merge.assert_called_once()

    def test_fuse_calls_fusion_module(self) -> None:
        sentinel = {"id": "out", "pages": 3, "sections": 1}
        with patch("tfv2.product.fusion.fuse_materials", return_value=dict(sentinel)) as fuse, \
                patch("tfv2.product.combine.service.artifact_path", return_value=None):
            result = combine_materials("out", MATERIALS, merge=True, mode="fuse", author=False)
        self.assertEqual(result["mode"], "fuse")
        self.assertTrue(result["merge"])
        fuse.assert_called_once()

    def test_material_without_pages_rejected(self) -> None:
        with self.assertRaises(ValueError):
            combine_materials("out", [{"artifact_id": "a", "pages": []}], merge=False)

    def test_empty_materials_rejected(self) -> None:
        with self.assertRaises(ValueError):
            combine_materials("out", [], merge=True)


if __name__ == "__main__":
    unittest.main()
