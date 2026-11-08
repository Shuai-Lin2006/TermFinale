"""课程级检索：问题能找到包含它的页；无关问题不硬凑。"""
from __future__ import annotations

import unittest

from core.retrieval import build_index, search

PAGES = [
    "【《高数》第 1 页】\n隐函数求导：方程两边对 x 求导，再解出 y'。",
    "【《高数》第 2 页】\n参数方程求导：dy/dx=(dy/dt)/(dx/dt)。",
    "【《高数》第 3 页】\n定积分换元法与分部积分。",
]


class RetrievalTest(unittest.TestCase):
    def test_finds_implicit_page(self):
        idx = build_index(PAGES, "高数")
        hits = search(idx, "隐函数求导怎么求")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["page"], 1)

    def test_param_page(self):
        idx = build_index(PAGES, "高数")
        hits = search(idx, "参数方程二阶导")
        self.assertEqual(hits[0]["page"], 2)

    def test_unrelated_returns_empty(self):
        idx = build_index(PAGES, "高数")
        self.assertEqual(search(idx, "量子力学波函数坍缩"), [])
