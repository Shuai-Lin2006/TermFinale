"""Section normalization only adds metadata and a summary block."""
from __future__ import annotations
import unittest
from tfv2.authoring.normalize import normalize_section
from tfv2.domain.lecture import LectureBlock, LectureSection, SourceRef, BlockKind


class Tests(unittest.TestCase):
    def test_fill(self):
        sec = LectureSection(id="s", title="t", blocks=[LectureBlock(id="b", kind=BlockKind.PARAGRAPH, text="第一页", source_refs=[SourceRef(material="m", page_start=1, page_end=1)])])
        normalize_section(sec, [1, 2])
        self.assertEqual(sec.objectives, [])  # 不再用模板空话填空
        self.assertTrue(any(b.kind == BlockKind.SUMMARY for b in sec.blocks))
        self.assertTrue(any(r.page_end == 2 for b in sec.blocks for r in b.source_refs))


if __name__ == "__main__":
    unittest.main()
