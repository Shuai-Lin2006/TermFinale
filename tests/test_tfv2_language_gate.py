"""语言门禁测试。"""
from __future__ import annotations

import unittest

from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef
from tfv2.domain.page import Page, PageLedger
from tfv2.quality.language_gate import check_language
from tests.test_tfv2_lecture import make_spec, src


class LanguageGateTests(unittest.TestCase):
    def test_english_terms_must_survive(self) -> None:
        spec = make_spec()
        spec.language_policy.source_lang = "English"
        spec.language_policy.gen_lang = "中文"
        spec.sections[0].blocks = [LectureBlock(id="b", kind=BlockKind.PARAGRAPH,
            text="反应速率 reaction rate 与活化能 activation energy。", source_refs=[src(1)])]
        ledger = PageLedger(material="x", page_count=1,
            pages=[Page(material="x", page_no=1, text="Reaction rate and activation energy.")],
            source_hash="x", parser_version="x")
        report = check_language(spec, ledger)
        self.assertEqual(report.passed, True)
        self.assertIn("reaction", report.preserved_terms)
        self.assertIn("activation", report.preserved_terms)

    def test_hant_simplified_warning(self) -> None:
        spec = make_spec()
        spec.language_policy.gen_lang = "繁體中文"
        spec.sections[0].blocks = [LectureBlock(id="b", kind=BlockKind.PARAGRAPH,
            text="这个电路的时间问题。", source_refs=[src(1)])]
        report = check_language(spec)
        self.assertTrue(any(x.code == "language.hant_simplified" for x in report.issues))

    def test_missing_terms_fails(self) -> None:
        spec = make_spec()
        spec.language_policy.source_lang = "English"
        spec.sections[0].blocks = [LectureBlock(id="b", kind=BlockKind.PARAGRAPH,
            text="这是全中文的讲解。", source_refs=[src(1)])]
        ledger = PageLedger(material="x", page_count=1,
            pages=[Page(material="x", page_no=1, text="Reaction rate and activation energy.")],
            source_hash="x", parser_version="x")
        report = check_language(spec, ledger)
        self.assertFalse(report.passed)


if __name__ == "__main__":
    unittest.main()
