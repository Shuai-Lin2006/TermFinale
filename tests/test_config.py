"""密钥加载与保存测试（使用临时数据目录，不碰真实 .env）。"""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("TERMFINALE_HOME", tempfile.mkdtemp(prefix="tf_cfg_"))
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("DASHSCOPE_API_KEY", None)

from core import config  # noqa: E402


class ConfigTest(unittest.TestCase):
    def test_missing_then_save(self):
        self.assertIn("DEEPSEEK_API_KEY", config.missing_keys())

        path = config.save_key("DEEPSEEK_API_KEY", "sk-test-123")
        self.assertTrue(path.exists())
        self.assertIn("DEEPSEEK_API_KEY=sk-test-123", path.read_text(encoding="utf-8"))
        self.assertNotIn("DEEPSEEK_API_KEY", config.missing_keys())

    def test_env_path_under_override(self):
        self.assertIn("tf_cfg_", str(config.user_env_path()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
