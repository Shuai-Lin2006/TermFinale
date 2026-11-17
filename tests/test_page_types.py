"""Page type classifier."""
from __future__ import annotations
import unittest
from tfv2.canonical.page_types import PageType, classify_page


class Tests(unittest.TestCase):
    def test_content(self):
        self.assertEqual(classify_page("镜像电流源由两个特性相同的晶体管组成，输出电流由参考电流决定。" * 2), PageType.CONTENT)

    def test_exercise(self):
        self.assertEqual(classify_page("习题\n1. 求电流\nA. 1\nB. 2\nC. 3\nD. 4"), PageType.EXERCISE)

    def test_empty(self):
        self.assertEqual(classify_page(""), PageType.EMPTY)


if __name__ == "__main__":
    unittest.main()
