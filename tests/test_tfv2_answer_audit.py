"""例题审计解析测试（不调用真实模型）。"""
from __future__ import annotations

import unittest

from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef
from tfv2.domain.page import Page, PageLedger
from tfv2.quality.answer_audit import audit_sections


class FakeClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = 0

    def json(self, system: str, user: str, *, max_tokens: int = 4096, temperature: float = 0.35) -> dict:
        self.calls += 1
        return self.payload


def ledger() -> PageLedger:
    return PageLedger(
        material="资料.pdf", page_count=2,
        pages=[Page(material="资料.pdf", page_no=1, text="环丙烷键角60度"),
               Page(material="资料.pdf", page_no=2, text="角张力公式")],
        source_hash="sha256:test", parser_version="test",
    )


class AnswerAuditTests(unittest.TestCase):
    def test_ok_result(self) -> None:
        sec = LectureSection(
            id="s", title="角张力",
            blocks=[LectureBlock(id="b", kind=BlockKind.EXAMPLE, text="例题：60度",
                                 source_refs=[SourceRef(material="资料.pdf", page_start=1, page_end=1)])],
            source_refs=[SourceRef(material="资料.pdf", page_start=1, page_end=1)],
        )
        client = FakeClient({"verdict": "ok", "confidence": 0.9, "reason": "资料有依据"})
        out = audit_sections(client, ledger(), [sec])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].verdict, "ok")
        self.assertEqual(client.calls, 1)

    def test_fix_result_keeps_corrected_text(self) -> None:
        sec = LectureSection(
            id="s", title="角张力",
            blocks=[LectureBlock(id="b", kind=BlockKind.EXAMPLE, text="例题：60度",
                                 source_refs=[SourceRef(material="资料.pdf", page_start=1, page_end=1)])],
            source_refs=[SourceRef(material="资料.pdf", page_start=1, page_end=1)],
        )
        client = FakeClient({"verdict": "fix", "confidence": 0.8, "reason": "公式错",
                             "corrected_text": "修正后的例题"})
        out = audit_sections(client, ledger(), [sec])
        self.assertEqual(out[0].verdict, "fix")
        self.assertEqual(out[0].corrected_text, "修正后的例题")


if __name__ == "__main__":
    unittest.main()
