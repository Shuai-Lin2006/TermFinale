import unittest
from tfv2.domain.page_unit import build_page_unit, classify_page


class PageUnitTests(unittest.TestCase):
    def test_clean_text(self):
        self.assertEqual(classify_page("这是普通讲义正文。"), "text")

    def test_private_or_control_falls_back_to_image(self):
        self.assertEqual(classify_page("公式 U\ue000 坏了"), "image")
        self.assertEqual(classify_page("控制\x01字符"), "image")
        self.assertEqual(classify_page("   "), "image")

    def test_formula_and_table(self):
        self.assertEqual(classify_page("∫ f dx ∑ a ≈ b ∀x"), "formula")
        self.assertEqual(build_page_unit(2, "a|b|c\nd|e|f\ng|h|i\nj|k|l").kind, "table")

    def test_build_unit_cleans_text(self):
        u = build_page_unit(3, "正常文本\x01带控制")
        self.assertEqual(u.kind, "image")
        self.assertEqual(u.text, "")


if __name__ == "__main__":
    unittest.main()
