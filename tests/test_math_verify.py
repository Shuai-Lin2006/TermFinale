
"""SymPy math checks for generated answers (deterministic, no model)."""
from __future__ import annotations

import unittest

from tfv2.quality import math_verify


class MathVerifyTests(unittest.TestCase):
    def test_catches_answer_analysis_mismatch(self) -> None:
        q = {"qtype": "fill_blank", "answer_text": "-\\frac{2}{e^2}",
             "analysis": "解得 y=-1/e，最终 y'' = \\frac{1}{e^2}。"}
        result = math_verify.audit_answer(q)
        self.assertTrue(result["checked"])
        self.assertTrue(result["issues"])

    def test_same_answer_passes(self) -> None:
        q = {"qtype": "calculation", "answer_text": "1/2",
             "analysis": "所以答案为 1/2。"}
        result = math_verify.audit_answer(q)
        self.assertEqual(result["issues"], [])

    def test_does_not_compare_number_with_function(self) -> None:
        q = {"qtype": "fill_blank", "answer_text": "\\frac{5^{10}-1}{2}",
             "analysis": "最后得到 \\sin 2x \\sin 3x。"}
        result = math_verify.audit_answer(q)
        self.assertEqual(result["issues"], [])

    def test_arithmetic_claim(self) -> None:
        issues = math_verify.check_arithmetic("2+3=6")
        self.assertTrue(issues)


if __name__ == "__main__":
    unittest.main()
