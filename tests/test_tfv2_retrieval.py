"""本地检索测试。"""
from __future__ import annotations

import unittest

from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef
from tfv2.retrieval import Chunk, RetrievalIndex, build_index, expand_neighbors, search, sources


def section(title: str, text: str, page: int) -> LectureSection:
    ref = SourceRef(material="x.pdf", page_start=page, page_end=page)
    return LectureSection(id=title, title=title, blocks=[
        LectureBlock(id=f"{title}-b", kind=BlockKind.PARAGRAPH, text=text, source_refs=[ref])
    ], source_refs=[ref])


class RetrievalTests(unittest.TestCase):
    def test_short_query_finds_chunk(self) -> None:
        idx = build_index("x", [section("角张力", "环丙烷的角张力是 24.8 度。", 6),
                                section("构象", "椅式比船式稳定。", 9)])
        hits = search(idx, "张力")
        self.assertTrue(hits)
        self.assertEqual(hits[0].section, "角张力")

    def test_latex_unit_is_searchable(self) -> None:
        text = r"9mA 电流源、6kΩ 电阻、$2\,\mu\mathrm{F}$ 电容，$u_C(0_+)=54\,\text{V}$。"
        idx = build_index("x", [section("3.4 三要素法", text, 52),
                                section("其他", "完全无关。", 9)])
        hits = search(idx, "9mA 例题的初始值和稳态值")
        self.assertTrue(hits)
        self.assertEqual(hits[0].section, "3.4 三要素法")

    def test_neighbor_expansion_keeps_late_hit(self) -> None:
        chunks = [
            Chunk(id=f"c{i}", section=f"s{i // 3}", anchor=f"s{i // 3}", pages=[i + 1], text=f"x{i}")
            for i in range(20)
        ]
        idx = RetrievalIndex(artifact_id="x", chunks=chunks)
        hits = [chunks[0], chunks[1], chunks[2], chunks[3], chunks[4], chunks[-1]]
        out = expand_neighbors(idx, hits, max_chunks=10)
        self.assertIn(chunks[-1].id, [c.id for c in out])

    def test_selection_boost_and_sources(self) -> None:
        idx = build_index("x", [section("构象", "椅式构象中 a 键朝上。", 9),
                                section("其他", "别的段落。", 10)])
        hits = search(idx, "这是什么", selection="椅式")
        self.assertEqual(hits[0].section, "构象")
        self.assertEqual(sources(hits)[0]["anchor"], "构象")


if __name__ == "__main__":
    unittest.main()
