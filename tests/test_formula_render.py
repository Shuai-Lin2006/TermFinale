"""Round 14: formula image fallback for HTML/PDF/Word."""
from __future__ import annotations

import unittest

from tfv2.render.formula_image import formula_data_uri, formula_png
from tfv2.render.lecture_html import _safe_formula_prose


class FormulaImageTests(unittest.TestCase):
    def test_clean_formula_renders_to_png(self):
        png = formula_png(r"\frac{a+b}{c-d}")
        self.assertIsNotNone(png)
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_unsupported_structure_returns_none(self):
        self.assertIsNone(formula_png(r"\chemfig{*6(-=-=)}"))

    def test_mathrm_is_left_for_katex(self):
        html = _safe_formula_prose(r"$\mathrm{x}^2$")
        self.assertIn("\\mathrm", html)
        self.assertNotIn("formula-img", html)

    def test_data_uri_is_png(self):
        uri = formula_data_uri(r"x^2+y^2=r^2")
        self.assertTrue(uri.startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
