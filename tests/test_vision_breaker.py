"""视觉模型连续超时要熔断：不能让讲义生成白等几分钟。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import ai_vision


class _Boom:
    class chat:
        class completions:
            @staticmethod
            def create(**kwargs):
                raise TimeoutError("timed out")


class _Ok:
    class chat:
        class completions:
            @staticmethod
            def create(**kwargs):
                class R:
                    class C:
                        class M:
                            content = "放大电路静态工作点示意"
                        message = M()
                    choices = [C()]
                return R()


class VisionBreakerTests(unittest.TestCase):
    def setUp(self) -> None:
        ai_vision.reset_vision_breaker()
        from PIL import Image
        self._tmp = tempfile.TemporaryDirectory()
        self.png = Path(self._tmp.name) / "p.png"
        Image.new("RGB", (8, 8), "white").save(self.png)

    def tearDown(self) -> None:
        ai_vision.reset_vision_breaker()
        self._tmp.cleanup()

    def test_opens_after_two_failures_and_skips_calls(self) -> None:
        calls = {"n": 0}

        class CountingBoom(_Boom):
            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        calls["n"] += 1
                        raise TimeoutError("timed out")

        with patch.object(ai_vision, "client", CountingBoom()), \
             patch.object(ai_vision, "logger"):
            self.assertEqual(ai_vision.analyze_teaching_figure(str(self.png)), "")
            self.assertEqual(ai_vision.analyze_teaching_figure(str(self.png)), "")
            self.assertFalse(ai_vision.vision_available())
            self.assertEqual(ai_vision.analyze_teaching_figure(str(self.png)), "", "熔断后不再调用模型")
        self.assertEqual(calls["n"], 2, "只该失败两次就熔断")

    def test_success_resets_counter(self) -> None:
        with patch.object(ai_vision, "client", _Boom()), patch.object(ai_vision, "logger"):
            ai_vision.analyze_teaching_figure(str(self.png))
        with patch.object(ai_vision, "client", _Ok()), patch.object(ai_vision, "logger"):
            self.assertTrue(ai_vision.analyze_teaching_figure(str(self.png)))
        self.assertTrue(ai_vision.vision_available(), "成功一次应重置失败计数")
