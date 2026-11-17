"""Price table: configured only, otherwise None."""
from __future__ import annotations

import os
import unittest

from tfv2.llm import pricing


class PricingTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("TERMFINALE_PRICE_JSON", None)

    def test_no_config_returns_none(self):
        os.environ.pop("TERMFINALE_PRICE_JSON", None)
        self.assertIsNone(pricing.estimate({"m": {"prompt_tokens": 1, "completion_tokens": 1}}))

    def test_configured_price(self):
        os.environ["TERMFINALE_PRICE_JSON"] = '{"m":{"input":2,"output":8}}'
        cost = pricing.estimate({"m": {"prompt_tokens": 1_000_000, "completion_tokens": 500_000}})
        self.assertAlmostEqual(cost, 6.0, places=4)

    def test_unknown_model_returns_none(self):
        os.environ["TERMFINALE_PRICE_JSON"] = '{"m":{"input":2,"output":8}}'
        self.assertIsNone(pricing.estimate({"other": {"prompt_tokens": 10, "completion_tokens": 10}}))


if __name__ == "__main__":
    unittest.main()
