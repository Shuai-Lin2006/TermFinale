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


class RepairTest(unittest.TestCase):
    def test_repairs_only_with_source_match(self):
        from core.quality.evidence import repair_citations
        md = "### 隐函数\n\n方程两边对 x 求导再解出 y'，这是隐函数求导的核心。"
        out, n = repair_citations(md, PAGES)
        self.assertEqual(n, 1)
        self.assertIn("（P.1）", out)

    def test_unrelated_not_repaired(self):
        from core.quality.evidence import repair_citations
        md = "### 无关\n\n量子力学波函数坍缩与薛定谔方程。"
        out, n = repair_citations(md, PAGES)
        self.assertEqual(n, 0)
        self.assertNotIn("（P.", out)


class IndexSectionTest(unittest.TestCase):
    def test_index_section_not_evidence(self):
        md = ("### 隐函数\n\n隐函数求导：方程两边对 x 求导，再解出 y'（P.1）。\n\n"
              "## 资料页码索引\n\n> 原文：【本页无可用文字】（P.2）\n")
        r = audit_evidence(md, PAGES)
        self.assertEqual(r.total, 1)
        self.assertEqual(r.supported, 1)

class MergedParagraphTest(unittest.TestCase):
    def test_quote_plus_explanation_supported(self):
        md = ("方程两边对 x 求导，再解出 y'。这一句讲解是为了帮助学生理解隐函数求导的核心步骤。"
              "（P.1）")
        r = audit_evidence(md, PAGES)
        self.assertEqual(r.supported, 1)
