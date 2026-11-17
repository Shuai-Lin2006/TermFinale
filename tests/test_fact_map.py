"""Deterministic fact coverage must not depend on a model judge."""
from __future__ import annotations

import unittest

from tfv2.authoring.page_facts import extract_page_facts
from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef
from tfv2.quality.fact_map import facts_for_pages, map_facts


class FactMapTests(unittest.TestCase):
    def test_extract_and_map(self):
        text = {1: "定义：放大倍数是指输出与输入之比。注意不能把负载算进去。图5-18给出曲线。"}
        facts = facts_for_pages(text, [1], per_page=5)
        self.assertTrue(facts)
        sec = LectureSection(id="s1", title="放大倍数", blocks=[
            LectureBlock(id="b1", kind=BlockKind.PARAGRAPH,
                         text="放大倍数是指输出与输入之比。注意不能把负载算进去。图5-18给出曲线。",
                         source_refs=[SourceRef(material="x", page_start=1, page_end=1)])],
            source_refs=[SourceRef(material="x", page_start=1, page_end=1)])
        result = map_facts(facts, [sec])
        self.assertGreaterEqual(result["covered"], 1)
        self.assertTrue(any(x["block_id"] == "b1" for x in result["facts"] if x["status"] == "covered"))

    def test_no_fabrication_on_empty(self):
        self.assertEqual(facts_for_pages({1: ""}, [1]), [])


if __name__ == "__main__":
    unittest.main()
