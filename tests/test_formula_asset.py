import unittest

from tfv2.render.formula_asset import build_formula_asset, classify_formula


class FormulaAssetTests(unittest.TestCase):
    def test_subject_classification(self) -> None:
        self.assertEqual(classify_formula(r"\ce{H2SO4}"), "chemistry")
        self.assertEqual(classify_formula(r"\chemfig{*6(-=-=)}"), "structure")
        self.assertEqual(classify_formula(r"\vec{F}=m\vec{a}"), "physics")
        self.assertEqual(classify_formula(r"\frac{a}{b}"), "math")

    def test_never_leaks_raw_tex(self) -> None:
        for src in (r"\ce{2H2 + O2 -> 2H2O}", r"\frac{a}{b}", r"\unknown{x}"):
            a = build_formula_asset(src)
            self.assertFalse(a.has_raw_latex, (src, a.display, a.typst))
            self.assertTrue(a.display)

    def test_structure_uses_source_fallback(self) -> None:
        a = build_formula_asset(r"\chemfig{*6(-=-=)}")
        self.assertEqual(a.renderer, "source_image")
        self.assertIn("结构式", a.display)


if __name__ == "__main__":
    unittest.main()
