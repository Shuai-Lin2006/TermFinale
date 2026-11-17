"""Kimi client is optional and never silently uses an empty key."""
from __future__ import annotations
import unittest
from unittest.mock import patch
from tfv2.llm.client import LLMError
from tfv2.llm.kimi import KimiClient


class Tests(unittest.TestCase):
    def test_missing_key(self):
        with patch("tfv2.llm.kimi.config.get_key", return_value=""):
            with self.assertRaises(LLMError):
                KimiClient()


if __name__ == "__main__":
    unittest.main()
