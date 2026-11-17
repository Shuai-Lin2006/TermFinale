"""失败提示要能照着做：不甩类名，给原因 + 下一步。"""
from __future__ import annotations

import unittest

from tfv2.llm.client import LLMError
from tfv2.product import exam
from tfv2.product.errors import friendly_reason


class FriendlyReasonTests(unittest.TestCase):
    def test_generic_exception_hides_class_name(self) -> None:
        got = friendly_reason(RuntimeError("模型没有返回 questions"))
        self.assertNotIn("RuntimeError", got)
        self.assertIn("模型没有返回 questions", got)
        self.assertIn("重试", got)

    def test_exam_missing_sections_points_to_next_step(self) -> None:
        got = friendly_reason(exam.ExamError("这份资料还没有讲义结构（缺 sections.json），不能出卷"))
        self.assertIn("生成讲义", got)

    def test_timeout_hint(self) -> None:
        got = friendly_reason(RuntimeError("请求超时 timeout after 180s"))
        self.assertIn("超时", got)
        self.assertIn("少选几页", got)

    def test_api_key_hint(self) -> None:
        got = friendly_reason(LLMError("API Key 无效或已过期。"))
        self.assertIn("设置", got)

    def test_empty_reason_still_actionable(self) -> None:
        got = friendly_reason(ValueError(""))
        self.assertIn("重试", got)

    def test_long_reason_truncated(self) -> None:
        got = friendly_reason(RuntimeError("x" * 500))
        self.assertLessEqual(len(got), 240)


class ExtractionRetryTests(unittest.TestCase):
    """提取的模型调用也要扛一次坏输出。"""

    def test_retry_recovers_from_empty_json(self) -> None:
        from tfv2.product import tasks

        class Client:
            def __init__(self):
                self.calls = 0

            def json(self, *a, **k):
                self.calls += 1
                return {} if self.calls == 1 else {"items": []}

        c = Client()
        self.assertEqual(tasks._json(c, "s", "u"), {"items": []})
        self.assertEqual(c.calls, 2)

    def test_two_bad_outputs_raise_task_error(self) -> None:
        from tfv2.product import tasks

        class Client:
            def json(self, *a, **k):
                return {}

        with self.assertRaises(tasks.TaskError):
            tasks._json(Client(), "s", "u")

    def test_llm_error_retried_then_raised(self) -> None:
        from tfv2.product import tasks
        from tfv2.llm.client import LLMError

        class Client:
            def __init__(self):
                self.calls = 0

            def json(self, *a, **k):
                self.calls += 1
                raise LLMError("连接失败")

        c = Client()
        with self.assertRaises(tasks.TaskError):
            tasks._json(c, "s", "u")
        self.assertEqual(c.calls, 2)
