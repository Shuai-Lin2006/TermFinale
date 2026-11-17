"""Release guard: provider failures become actionable, non-secret messages."""
from __future__ import annotations

import unittest

from tfv2.llm.client import describe_llm_error


class _ProviderError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class LLMErrorMessagesTest(unittest.TestCase):
    def test_expired_key(self):
        msg = describe_llm_error(_ProviderError("Invalid API key", 401))
        self.assertIn("Key", msg)
        self.assertIn("设置", msg)

    def test_billing(self):
        msg = describe_llm_error(_ProviderError("Insufficient Balance", 402))
        self.assertIn("余额不足", msg)

    def test_rate_limit(self):
        msg = describe_llm_error(_ProviderError("rate limit", 429))
        self.assertIn("频繁", msg)

    def test_timeout_like_detail_is_bounded(self):
        msg = describe_llm_error(_ProviderError("x" * 1000, 500))
        self.assertLessEqual(len(msg), 260)
        self.assertNotIn("sk-", msg)


if __name__ == "__main__":
    unittest.main()
