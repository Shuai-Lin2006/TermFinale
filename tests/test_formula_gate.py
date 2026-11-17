"""Round 13: formula LaTeX quality gate."""
from __future__ import annotations

import unittest

from tfv2.product import generate


class FormulaGateTests(unittest.TestCase):
    def test_clean_formula_passes(self):
        for latex in (r"\frac{a+b}{c-d}", r"x^2+y^2=r^2", r"\int_0^1 x\,dx", r"\sqrt{x+1}"):
            self.assertTrue(generate._latex_ok(latex), latex)

    def test_scaffolding_is_rejected(self):
        for latex in ("", r"\Big( x \Big)", r"\begin{array}{c} x \end{array}", r"\otimes"):
            self.assertFalse(generate._latex_ok(latex), latex)

    def test_common_relations_pass(self):
        self.assertTrue(generate._latex_ok(r"a \le b"))
        self.assertTrue(generate._latex_ok(r"\alpha+\beta=\gamma"))


if __name__ == "__main__":
    unittest.main()
