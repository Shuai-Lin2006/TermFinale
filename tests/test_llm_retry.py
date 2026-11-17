"""模型调用要能扛住网络抖动：瞬时错误重试，配置错误立即失败。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

class APIConnectionError(Exception):
    pass


class RateLimitError(Exception):
    status_code = 429


class AuthenticationError(Exception):
    status_code = 401

from tfv2.llm import client as llm


class _Resp:
    class _Choice:
        class _Msg:
            content = '{"ok": true}'

        message = _Msg()

    choices = [_Choice()]


class _FakeCompletions:
    def __init__(self, failures: list[Exception]) -> None:
        self.failures = list(failures)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return _Resp()


class _FakeChat:
    def __init__(self, failures: list[Exception]) -> None:
        self.completions = _FakeCompletions(failures)


class RetryTests(unittest.TestCase):
    def _client(self, failures: list[Exception]):
        with patch.object(llm.DeepSeekClient, "__init__", lambda self, *a, **k: None):
            c = llm.DeepSeekClient()
        c._model = "deepseek-chat"
        c._effort = None
        c._client = type("C", (), {"chat": _FakeChat(failures)})()
        return c

    def test_retryable_error_then_success(self) -> None:
        c = self._client([APIConnectionError("connection reset")])
        with patch.object(llm.time, "sleep"), patch.object(llm.token_budget, "check"):
            got = c.json("s", "u")
        self.assertEqual(got, {"ok": True})
        self.assertEqual(c._client.chat.completions.calls, 2)

    def test_rate_limit_retried(self) -> None:
        c = self._client([RateLimitError("429 too many requests")])
        with patch.object(llm.time, "sleep"), patch.object(llm.token_budget, "check"):
            self.assertEqual(c.json("s", "u"), {"ok": True})
        self.assertEqual(c._client.chat.completions.calls, 2)

    def test_auth_error_not_retried(self) -> None:
        c = self._client([AuthenticationError("invalid api key")])
        with patch.object(llm.time, "sleep") as sleep, patch.object(llm.token_budget, "check"):
            with self.assertRaises(llm.LLMError):
                c.json("s", "u")
        self.assertEqual(c._client.chat.completions.calls, 1)
        sleep.assert_not_called()

    def test_gives_up_after_max_attempts(self) -> None:
        c = self._client([APIConnectionError("timeout")] * 5)
        with patch.object(llm.time, "sleep"), patch.object(llm.token_budget, "check"):
            with self.assertRaises(llm.LLMError):
                c.json("s", "u")
        self.assertEqual(c._client.chat.completions.calls, llm.MAX_ATTEMPTS)
