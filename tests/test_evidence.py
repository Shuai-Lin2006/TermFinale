"""逐句证据审计：有页码但页不支持，必须标低依据。"""
from __future__ import annotations

import unittest

from core.quality.evidence import audit_evidence


PAGES = [
    "【《高数》第 1 页】\n隐函数求导：方程两边对 x 求导，再解出 y'。",
    "【《高数》第 2 页】\n参数方程求导：dy/dx=(dy/dt)/(dx/dt)。",
]


class EvidenceTest(unittest.TestCase):
    def test_supported_claim(self):
        md = "### 隐函数求导\n\n方程两边对 x 求导再解出 y'，这是隐函数求导的核心。（P.1）"
        r = audit_evidence(md, PAGES)
        self.assertEqual(r.total, 1)
        self.assertEqual(r.supported, 1)

    def test_citation_to_wrong_page_is_unsupported(self):
        md = "### 隐函数求导\n\n这里讲的是完全无关的量子力学与波函数坍缩。（P.2）"
        r = audit_evidence(md, PAGES)
        self.assertEqual(r.total, 1)
        self.assertEqual(r.unsupported, 1)
        self.assertTrue(r.unsupported_samples)

    def test_no_citation(self):
        md = "### 结论\n\n这是一段没有任何页码依据的长文本内容。"
        r = audit_evidence(md, PAGES)
        self.assertEqual(r.total, 1)
        self.assertEqual(r.no_citation, 1)
