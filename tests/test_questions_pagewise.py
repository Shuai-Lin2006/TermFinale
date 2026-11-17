"""Pagewise questions: per-page call + no invented items."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tfv2.product import questions_pagewise


class PagewiseQuestionTests(unittest.TestCase):
    def test_one_page(self):
        doc = {"content": {"items": [{"no": "1", "qtype": "choice", "stem": "题干",
                                      "options": ["A", "B", "C", "D"], "answer_text": "A",
                                      "quote": "题干", "page": 1}]}}
        with patch.object(questions_pagewise.tasks, "_extract", return_value=doc):
            out = questions_pagewise.extract_pages({1: "1. 题干\nA B C D\n【答案】A"}, [1], object(), workers=1)
        self.assertEqual(len(out["items"]), 1)
        self.assertEqual(out["coverage"], 1.0)


if __name__ == "__main__":
    unittest.main()
