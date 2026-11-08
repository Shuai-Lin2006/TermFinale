"""缓存统计与调试产物清理测试。

注意：必须在导入 core.paths 之前设置 TERMFINALE_HOME，否则会用到真实用户目录。
"""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("TERMFINALE_HOME", tempfile.mkdtemp(prefix="tf_maint_"))

from core import maintenance, paths  # noqa: E402


class MaintenanceTest(unittest.TestCase):
    def test_report_and_prune(self):
        paths.ensure_dirs()
        for p in paths.debug_dir().iterdir():
            if p.is_file():
                p.unlink()
        for i in range(5):
            (paths.debug_dir() / f"f{i}.md").write_text("x" * (i + 1), encoding="utf-8")

        report = maintenance.cache_report()
        for key in ("assets", "debug", "logs", "outputs"):
            self.assertIn(key, report)
        self.assertGreaterEqual(report["debug"]["files"], 5)

        result = maintenance.prune_debug(keep=2)
        self.assertEqual(result["removed"], 3)
        self.assertEqual(len([p for p in paths.debug_dir().iterdir() if p.is_file()]), 2)

    def test_human_size(self):
        self.assertEqual(maintenance.human_size(999), "999B")
        self.assertEqual(maintenance.human_size(2048), "2.0KB")


if __name__ == "__main__":
    unittest.main(verbosity=2)
