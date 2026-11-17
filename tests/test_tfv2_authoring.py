"""v2 小节生成测试（假 LLM，不耗真实 API）。"""
from __future__ import annotations

import unittest

from tfv2.authoring.lecture import AuthoringError, author_section, build_evidence_packet, coverage_cues
from tfv2.domain.page import Page, PageLedger


def ledger() -> PageLedger:
    pages = [Page(material="环烃.pptx", page_no=i, text=f"第{i}页 环烷烃的结构与张力") for i in range(1, 9)]
    return PageLedger(material="环烃.pptx", page_count=8, pages=pages,
                      source_hash="sha256:test", parser_version="test")


class FakeLLM:
    def __init__(self, payload: dict):
        self.payload = payload

    def json(self, system: str, user: str, *, max_tokens: int = 4096, temperature: float = 0.35) -> dict:
        return self.payload


GOOD = {
    "blocks": [
        {"kind": "paragraph", "text": "环烷烃的碳环不是平面，键角有偏差。", "source_pages": [6, 7]},
        {"kind": "example", "text": "以环丙烷为例，键角 60°，角张力最大。", "source_pages": [6]},
        {"kind": "pitfall", "text": "不要把环己烷的椅式当成平面六边形。", "source_pages": [7]},
        {"kind": "summary", "text": "环越小角张力越大，环己烷最稳定。", "source_pages": [6, 7]},
    ]
}


class SequenceLLM:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = 0

    def json(self, system: str, user: str, *, max_tokens: int = 4096, temperature: float = 0.35) -> dict:
        self.calls += 1
        return self.payloads[min(self.calls - 1, len(self.payloads) - 1)]


class AuthoringTests(unittest.TestCase):
    def test_valid_section(self) -> None:
        sec = author_section(
            FakeLLM(GOOD), ledger(),
            chapter_title="第四章 环烃",
            section_title="二、环烷烃的结构",
            pages=[6, 7, 8],
        )
        self.assertEqual(sec.title, "二、环烷烃的结构")
        self.assertGreaterEqual(len(sec.blocks), 4)
        self.assertTrue(any(b.kind.value == "summary" for b in sec.blocks))
        self.assertEqual(sec.blocks[0].source_refs[0].page_start, 6)
        self.assertEqual({r.page_start for r in sec.source_refs}, {6, 7})

    def test_short_section_is_retried(self) -> None:
        short = {"title": "短", "blocks": [{"kind": "paragraph", "text": "短。", "source_pages": [6]}]}
        long = {"title": "完整", "blocks": [
            {"kind": "paragraph", "text": f"第{i}段完整讲解，覆盖定义、公式和结论。" * 8, "source_pages": [6]}
            for i in range(6)
        ]}
        llm = SequenceLLM([short, long])
        sec = author_section(llm, ledger(), chapter_title="章", section_title="节", pages=[6, 7])
        self.assertGreaterEqual(len(sec.blocks), 6)
        self.assertTrue(any(b.kind.value == "summary" for b in sec.blocks))
        self.assertEqual(llm.calls, 2)

    def test_source_page_outside_pages_rejected(self) -> None:
        bad = {
            "blocks": [
                {"kind": "paragraph", "text": "编造", "source_pages": [99]},
            ]
        }
        with self.assertRaises(AuthoringError):
            author_section(FakeLLM(bad), ledger(), chapter_title="章", section_title="节", pages=[6, 7])

    def test_empty_blocks_rejected(self) -> None:
        with self.assertRaises(AuthoringError):
            author_section(FakeLLM({"blocks": []}), ledger(), chapter_title="章", section_title="节", pages=[6])

    def test_unknown_kind_rejected(self) -> None:
        bad = {"blocks": [{"kind": "video", "text": "x", "source_pages": [6]}]}
        with self.assertRaises(AuthoringError):
            author_section(FakeLLM(bad), ledger(), chapter_title="章", section_title="节", pages=[6])

    def test_coverage_cues_extract_grounded_lines(self) -> None:
        cues = coverage_cues(ledger(), [6, 7])
        self.assertTrue(cues)
        self.assertTrue(any("结构" in x for x in cues))

    def test_evidence_packet_has_page_markers(self) -> None:
        packet = build_evidence_packet(ledger(), [6, 7])
        self.assertIn("【第6页】", packet)
        self.assertIn("【第7页】", packet)


if __name__ == "__main__":
    unittest.main()
