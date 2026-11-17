"""密钥加载与保存测试（使用临时数据目录，不碰真实 .env）。"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("TERMFINALE_HOME", tempfile.mkdtemp(prefix="tf_cfg_"))
# 其它测试模块会 import core.exam_engine → load_env()；不跳过项目 .env 的话
# 真实密钥会漏进 os.environ，让"缺密钥"用例变成依赖开发机环境。
os.environ["TERMFINALE_SKIP_PROJECT_ENV"] = "1"
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("DASHSCOPE_API_KEY", None)

from core import config  # noqa: E402


class ConfigTest(unittest.TestCase):
    def test_missing_then_save(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            fake = Path(d) / ".env"
            with patch.object(config, "user_env_path", return_value=fake):
                config.save_key("DEEPSEEK_API_KEY", "sk-test-123")
                self.assertTrue(fake.exists())
                self.assertIn("DEEPSEEK_API_KEY=sk-test-123", fake.read_text(encoding="utf-8"))

    def test_env_path_under_override(self):
        # 全量测试下 TERMFINALE_HOME 可能先被其他模块设置；只验证 .env 位于当前数据根目录
        from core import paths
        self.assertEqual(config.user_env_path().parent, paths.data_dir())
        self.assertEqual(config.user_env_path().name, ".env")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class CourseMasteryPrefsTests(unittest.TestCase):
    """掌握度要能存下来，重新打开课程还在。"""

    def test_mastery_roundtrip(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from tfv2.product import store

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "product.sqlite3"
            with patch.object(store, "DB_PATH", db):
                store.save_course_prefs("c-test", 80, "2026-12-20", "测试课", credits=3,
                                        difficulty=3, mastery=4)
                got = store.get_course_prefs("c-test")
                self.assertEqual(got["mastery"], 4)
                self.assertEqual(got["exam_date"], "2026-12-20")

    def test_mastery_is_clamped(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from tfv2.product import store

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "product.sqlite3"
            with patch.object(store, "DB_PATH", db):
                store.save_course_prefs("c-test", 80, "", mastery=99)
                self.assertEqual(store.get_course_prefs("c-test")["mastery"], 5)


class CourseKeyTests(unittest.TestCase):
    """课程 key 必须稳定：产物、偏好、前端说的是同一门课。"""

    def test_key_is_deterministic_and_stable(self) -> None:
        from tfv2.product.service import course_key_for
        a = course_key_for("模拟电子技术")
        b = course_key_for("模拟电子技术")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("c-"))
        self.assertNotEqual(a, course_key_for("数学分析"))

    def test_known_subject_uses_meta_key(self) -> None:
        from tfv2.product.service import course_key_for
        self.assertEqual(course_key_for("电路"), "circuit")

    def test_save_sources_reuses_service_key(self) -> None:
        from pathlib import Path
        source = Path("tfv2/product/sources.py").read_text(encoding="utf-8")
        self.assertIn("course_key_for", source)
        self.assertNotIn('"c-" + uuid.uuid4().hex[:8]', source)
