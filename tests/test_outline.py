"""章名清洗：正文句子/编号不能当目录。"""
from __future__ import annotations

import unittest

from core.generate.outline import _clean_chapter_title


class ChapterTitleTest(unittest.TestCase):
    def test_good_title_kept(self):
        self.assertEqual(_clean_chapter_title("实数完备性与Cauchy列"), "实数完备性与Cauchy列")

    def test_sentence_falls_back_to_must_know(self):
        self.assertEqual(
            _clean_chapter_title("由于g 是连续函数，从而G(x) 是连续可微的。", ["连续函数的性质"]),
            "连续函数的性质")

    def test_number_title_falls_back_to_part(self):
        self.assertEqual(_clean_chapter_title("48.1", index=4), "第4部分")

    def test_note_prefix_stripped(self):
        self.assertEqual(_clean_chapter_title("注记. 线性映射的逼近"), "线性映射的逼近")


if __name__ == "__main__":
    unittest.main(verbosity=2)
