import unittest
from tfv2.quality.evidence_report import build_evidence_report, evidence_summary


class EvidenceReportTests(unittest.TestCase):
    def test_quotes_and_missing(self):
        class R:
            def __init__(self, page, quote=None):
                self.page_start = page; self.page_end = page; self.quote = quote
        class B:
            def __init__(self, id, text, refs): self.id=id; self.text=text; self.source_refs=refs; self.kind=type("K",(),{"value":"paragraph"})(); self.figure=None
        class S:
            title="节"; blocks=[B("a","内容",[R(1,"内容")]), B("b","无来源",[])]
        class Spec: sections=[S()]
        rows=build_evidence_report(Spec())
        self.assertEqual(rows[0]["status"],"quoted")
        self.assertEqual(rows[1]["status"],"missing")
        self.assertFalse(evidence_summary(rows)["passed"])


if __name__ == "__main__":
    unittest.main()
