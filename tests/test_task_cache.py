"""Task cache: second identical run must not call the model."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tfv2.product import service, tasks
from tests.test_tfv2_tasks import FakeClient


class TaskCacheTests(unittest.TestCase):
    def test_second_run_hits_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "artifacts"; root.mkdir()
            from tests.test_tfv2_tasks import artifact
            artifact(root, "cache_task_art")
            old = service.ARTIFACT_ROOTS
            service.ARTIFACT_ROOTS = [root]
            try:
                data = {"items": [{"point": "导数定义", "detail": "瞬时变化率", "quote": "导数表示瞬时变化率。", "page": 1}]}
                first = tasks.run_task("extract_points", "cache_task_art", "s1", client=FakeClient(data))
                second = tasks.run_task("extract_points", "cache_task_art", "s1", client=FakeClient())
                self.assertTrue(second.get("cache_hit"))
                self.assertEqual(len(second["content"]["items"]), len(first["content"]["items"]))
            finally:
                service.ARTIFACT_ROOTS = old


if __name__ == "__main__":
    unittest.main()
