"""Symbol tables must not be classified as teaching content."""
from __future__ import annotations
import unittest
from tfv2.canonical.page_types import PageType, classify_page


class Tests(unittest.TestCase):
    def test_symbol_table(self):
        text = "\n".join(f"符号{i}：这是第{i}个符号的说明" for i in range(12))
        self.assertEqual(classify_page(text), PageType.OVERVIEW)

    def test_content(self):
        self.assertEqual(classify_page("放大电路的核心是静态工作点。\n" * 10), PageType.CONTENT)


if __name__ == "__main__":
    unittest.main()
