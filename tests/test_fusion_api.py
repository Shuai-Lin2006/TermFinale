"""多资料拼接入口的硬规则：少于两份不拼接、页码越界拒绝、档位无交集拒绝。

这里只测校验路径，不真的生成产物（生成由 scripts/fusion_e2e.py 用真资料验收）。
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from tfv2.api.product_app import app as product_app


class FuseJobValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(product_app)

    def test_empty_materials_rejected(self) -> None:
        r = self.client.post("/api/lecture/fuse-jobs", json={"materials": [], "merge": True})
        self.assertEqual(r.status_code, 422)
        self.assertIn("至少选一份资料", r.json()["detail"])

    def test_merge_needs_at_least_two_materials(self) -> None:
        fake = {"page_count": 10, "id": "sel-test"}
        with patch("tfv2.api.product_app.service.get_artifact", return_value=fake):
            r = self.client.post("/api/lecture/fuse-jobs",
                                 json={"materials": [{"artifact_id": "sel-test", "pages": []}],
                                       "merge": True})
        self.assertEqual(r.status_code, 422)
        self.assertIn("至少要两份", r.json()["detail"])

    def test_page_out_of_range_rejected(self) -> None:
        fake = {"page_count": 5, "id": "sel-test"}
        with patch("tfv2.api.product_app.service.get_artifact", return_value=fake):
            r = self.client.post("/api/lecture/fuse-jobs",
                                 json={"materials": [{"artifact_id": "sel-test", "pages": [1, 9]},
                                                     {"artifact_id": "sel-test2", "pages": [1]}],
                                       "merge": False})
        self.assertEqual(r.status_code, 422)
        self.assertIn("页码超出范围", r.json()["detail"])

    def test_missing_artifact_rejected(self) -> None:
        with patch("tfv2.api.product_app.service.get_artifact", return_value=None):
            r = self.client.post("/api/lecture/fuse-jobs",
                                 json={"materials": [{"artifact_id": "sel-none", "pages": [1]}],
                                       "merge": False})
        self.assertEqual(r.status_code, 404)

    def test_merge_without_tier_intersection_rejected(self) -> None:
        # 20 页只能标准档，80 页只有精品/高范围：交集为空，不能悄悄降级。
        sizes = {"sel-a": 20, "sel-b": 80}

        def fake_artifact(aid: str):
            return {"page_count": sizes[aid], "id": aid}

        with patch("tfv2.api.product_app.service.get_artifact", side_effect=fake_artifact):
            r = self.client.post("/api/lecture/fuse-jobs",
                                 json={"materials": [{"artifact_id": "sel-a", "pages": []},
                                                     {"artifact_id": "sel-b", "pages": []}],
                                       "merge": True})
        self.assertEqual(r.status_code, 422)
        self.assertIn("交集", r.json()["detail"])


if __name__ == "__main__":
    unittest.main()


class LecturePlanEndpointTests(unittest.TestCase):
    """档位弹窗的数据源：页数 → 可用档位 + 覆盖目标。"""

    def setUp(self) -> None:
        self.client = TestClient(product_app)

    def _plan(self, totals, merge=False):
        return self.client.post("/api/lecture/plan", json={
            "merge": merge,
            "materials": [{"artifact_id": f"a{i}", "total_pages": n, "pages": []}
                          for i, n in enumerate(totals)],
        })

    def test_tiers_by_single_material_pages(self) -> None:
        cases = {50: ["standard"], 150: ["premium", "broad"],
                 200: ["normal", "premium", "broad"], 600: ["normal", "premium"],
                 1001: ["normal", "premium"]}
        for pages, tiers in cases.items():
            r = self._plan([pages])
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()["materials"][0]["tiers"], tiers, pages)

    def test_coverage_targets_match_product_rules(self) -> None:
        r = self._plan([200])
        self.assertEqual(r.json()["materials"][0]["coverage_targets"],
                         {"normal": 50, "premium": 65, "broad": 75})

    def test_merge_intersects_and_rejects_without_overlap(self) -> None:
        ok = self._plan([80, 200], merge=True)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["merge_tiers"], ["premium", "broad"])
        bad = self._plan([20, 80], merge=True)
        self.assertEqual(bad.status_code, 422)
        self.assertIn("交集", bad.json()["detail"])

    def test_large_material_has_no_broad_tier(self) -> None:
        r = self._plan([1001])
        self.assertNotIn("broad", r.json()["materials"][0]["tiers"])
