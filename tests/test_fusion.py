"""多资料自然融合的确定性部分：统一章节、去重、过渡、各自出处。

这里不调模型，也不读用户数据目录；真实产物回归在 scripts/fusion_e2e.py 里跑。
"""
from __future__ import annotations

import unittest
from pathlib import Path

from tfv2.domain.lecture import LectureSection, SourceRef
from tfv2.domain.page import Page, PageLedger, PageQuality
from tfv2.product import fusion


def _material(aid: str, label: str, pages: list[tuple[int, int, str]]) -> fusion.Material:
    """pages: (local_page, source_page, text)"""
    rows = [{"page": lp, "source_page": sp, "text": text} for lp, sp, text in pages]
    return fusion.Material(artifact_id=aid, label=label, pages=[r["page"] for r in rows], rows=rows)


class TitleTests(unittest.TestCase):
    def test_norm_title_drops_numbering_and_punctuation(self):
        self.assertEqual(fusion.norm_title("第一章 极限与连续"), fusion.norm_title("第1章 极限与连续"))
        self.assertEqual(fusion.norm_title("1.2 导数的定义"), fusion.norm_title("导数的定义"))
        self.assertEqual(fusion.norm_title("一、函数极限"), fusion.norm_title("函数极限"))

    def test_parse_order_prefers_numbers(self):
        self.assertEqual(fusion.parse_order("第三章 积分")[0], 3)
        self.assertEqual(fusion.parse_order("2.3 洛必达法则"), (2, 3))
        self.assertEqual(fusion.parse_order("没有编号的一节")[0], 9999)


class ChapterSplitTests(unittest.TestCase):
    def test_real_headings_become_chapters(self):
        mat = _material("a1", "高数.pdf", [
            (1, 1, "第一章 极限\n极限的直观含义"),
            (2, 2, "继续讲极限"),
            (3, 3, "第二章 导数\n导数的定义"),
            (4, 4, "求导法则"),
        ])
        chapters = fusion.chapters_of_material(mat)
        self.assertEqual([c.title for c in chapters], ["第一章 极限", "第二章 导数"])
        self.assertEqual([s.pages for c in chapters for s in c.spans], [[1, 2], [3, 4]])

    def test_pages_before_first_heading_are_kept(self):
        mat = _material("a1", "A.pdf", [
            (1, 10, "封面和一些说明"),
            (2, 11, "第一章 起点"),
            (3, 12, "正文"),
        ])
        chapters = fusion.chapters_of_material(mat)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].spans[0].pages, [1])
        self.assertIn("开篇", chapters[0].title)

    def test_no_heading_never_fakes_a_topic_title(self):
        mat = _material("a1", "扫描件.pdf", [(1, 40, "没有标题的正文")] * 1 + [(2, 41, "正文")])
        chapters = fusion.chapters_of_material(mat)
        self.assertTrue(chapters)
        for ch in chapters:
            self.assertIn("原文页段", ch.title)

    def test_every_page_lands_in_exactly_one_chapter(self):
        mat = _material("a1", "A.pdf", [
            (1, 1, "第一章 极限"),
            (2, 2, "正文"),
            (3, 3, "第二章 导数"),
            (4, 4, "正文"),
            (5, 5, "正文"),
        ])
        chapters = fusion.chapters_of_material(mat)
        seen = [p for c in chapters for s in c.spans for p in s.pages]
        self.assertEqual(sorted(seen), [1, 2, 3, 4, 5])
        self.assertEqual(len(seen), len(set(seen)))


class HeadingFilterTests(unittest.TestCase):
    def test_unit_lines_are_not_headings(self):
        for line in ("0.1 mA", "1.5 V", "3.3 kΩ"):
            self.assertFalse(fusion._looks_like_heading(line), line)

    def test_real_headings_without_space_still_count(self):
        self.assertTrue(fusion._looks_like_heading("1.3.4三极管的特性曲线"))
        self.assertTrue(fusion._looks_like_heading("第一章 极限"))
        self.assertTrue(fusion._looks_like_heading("一、填空题"))

    def test_formula_lines_are_not_headings(self):
        self.assertFalse(fusion._looks_like_heading("1.2 Ic = βIB + ICEO"))


class UniqueTitleTests(unittest.TestCase):
    def _ch(self, title: str, label: str, pages: list[int]) -> fusion.Chapter:
        span = fusion.MaterialSpan(artifact_id="x", label=label, pages=pages, source_pages=pages)
        return fusion.Chapter(title=title, key=fusion.norm_title(title), spans=[span])

    def test_duplicate_titles_get_material_and_page_suffix(self):
        chapters = fusion.unique_titles([
            self._ch("第 1–6 页（原文页段）", "A.pdf", [1, 2]),
            self._ch("第 1–6 页（原文页段）", "B.pdf", [3, 4]),
        ])
        self.assertEqual(len({c.title for c in chapters}), 2)
        self.assertIn("A", chapters[0].title)
        self.assertIn("B", chapters[1].title)

    def test_unique_titles_stay_untouched(self):
        chapters = fusion.unique_titles([self._ch("第一章 极限", "A.pdf", [1])])
        self.assertEqual(chapters[0].title, "第一章 极限")


class FuseChapterTests(unittest.TestCase):
    def _ch(self, title: str, aid: str, label: str, pages: list[int]) -> fusion.Chapter:
        span = fusion.MaterialSpan(artifact_id=aid, label=label, pages=pages, source_pages=pages)
        return fusion.Chapter(title=title, key=fusion.norm_title(title), spans=[span])

    def test_same_chapter_number_merges_across_materials(self):
        a = [self._ch("第一章 极限与连续", "a", "高数.pdf", [1, 2])]
        b = [self._ch("第一章 极限与连续", "b", "竞赛.pdf", [1, 2])]
        fused = fusion.fuse_chapters([a, b])
        self.assertEqual(len(fused), 1)
        self.assertEqual([s.label for s in fused[0].spans], ["高数.pdf", "竞赛.pdf"])

    def test_unrelated_chapters_stay_separate(self):
        a = [self._ch("第一章 极限", "a", "高数.pdf", [1])]
        b = [self._ch("第一章 线性空间", "b", "代数.pdf", [1])]
        # 章号相同但主题不同：不能因为“都是第一章”就合并。
        self.assertEqual(fusion.parse_order("第一章 极限")[0], fusion.parse_order("第一章 线性空间")[0])
        fused = fusion.fuse_chapters([a, b])
        self.assertEqual(len(fused), 2)

    def test_generic_suffix_title_merges(self):
        a = [self._ch("导数的定义", "a", "A.pdf", [1])]
        b = [self._ch("导数的定义概述", "b", "B.pdf", [2])]
        self.assertEqual(len(fusion.fuse_chapters([a, b])), 1)

    def test_merged_chapter_keeps_material_order(self):
        a = [self._ch("第一章 极限", "a", "A.pdf", [1]), self._ch("第二章 导数", "a", "A.pdf", [2])]
        b = [self._ch("第一章 极限", "b", "B.pdf", [1])]
        fused = fusion.fuse_chapters([a, b])
        self.assertEqual([c.title for c in fused], ["第一章 极限", "第二章 导数"])
        self.assertEqual(fused[0].materials, ["A.pdf", "B.pdf"])


class DedupeTests(unittest.TestCase):
    def setUp(self) -> None:
        fusion.reset_registry()

    def test_similarity_separates_related_from_unrelated(self):
        a = "函数在一点的极限存在，当且仅当左右极限存在且相等，这是判断分段函数的关键。"
        b = "函数在一点的极限存在，当且仅当左右极限都存在并且相等，这是判断分段函数的关键。"
        c = "矩阵的秩等于非零子式的最高阶数，行变换不改变秩。"
        self.assertGreater(fusion.similarity(a, b), fusion.DUPLICATE_THRESHOLD)
        self.assertLess(fusion.similarity(a, c), 0.3)

    def test_registry_finds_repeat_across_sources(self):
        body = ("极限的四则运算法则要求参与运算的两个极限都存在才能拆开计算，"
                "否则会得出错误结论；遇到无穷大减无穷大、零乘无穷大这类未定式，"
                "必须先化成可以判断的形式，再决定用等价无穷小、夹逼还是洛必达。"
                "这一步是这一章最常见也最致命的失分点，做题时先写“两极限存在”，"
                "再动手拆项，能省掉一大半的返工时间。")
        self.assertIsNone(fusion.find_duplicate(body))
        fusion.register_text(body, "第一章 极限", 3)
        hit = fusion.find_duplicate(body)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["chapter"], "第一章 极限")

    def test_short_text_is_never_flagged(self):
        fusion.register_text("极限存在", "第一章", 1)
        self.assertIsNone(fusion.find_duplicate("极限存在"))


class BackfillTests(unittest.TestCase):
    def test_missing_pages_are_filled_and_reported(self):
        uni = _universe([("a", "高数.pdf", 1, 10), ("a", "高数.pdf", 2, 11)],
                        ["第一页正文内容。", "第二页正文内容。"], offsets={"a": 0})
        chapter = fusion.Chapter(title="第一章", spans=[
            fusion.MaterialSpan("a", "高数.pdf", [1, 2], [10, 11])])
        sec = LectureSection(id="s", title="第一章", blocks=[
            {"id": "b1", "kind": "paragraph", "text": "模型只写了第一页",
             "source_refs": [{"material": "高数.pdf", "page_start": 1, "page_end": 1,
                              "source_page": 10}]}],
            source_refs=[{"material": "高数.pdf", "page_start": 1, "page_end": 1, "source_page": 10}])
        missing, patched = fusion.backfill_pages(sec, chapter, uni, index=1)
        self.assertEqual(missing, [2])
        self.assertEqual(len(patched.blocks), 2)
        self.assertIn("原文补充", patched.blocks[1].text)
        self.assertIn("第 11 页", patched.blocks[1].text)
        self.assertEqual(patched.blocks[1].source_refs[0].source_page, 11)

    def test_nothing_to_do_returns_same_section(self):
        uni = _universe([("a", "A.pdf", 1, 1)], ["正文内容。"], offsets={"a": 0})
        chapter = fusion.Chapter(title="第一章", spans=[
            fusion.MaterialSpan("a", "A.pdf", [1], [1])])
        sec = LectureSection(id="s", title="第一章", blocks=[
            {"id": "b1", "kind": "paragraph", "text": "写了这一页",
             "source_refs": [{"material": "A.pdf", "page_start": 1, "page_end": 1}]}],
            source_refs=[{"material": "A.pdf", "page_start": 1, "page_end": 1}])
        missing, patched = fusion.backfill_pages(sec, chapter, uni, index=1)
        self.assertEqual(missing, [])
        self.assertIs(patched, sec)


def _universe(origin_rows, texts, offsets=None) -> fusion.Universe:
    pages = [Page(material="fused", page_no=i + 1, text=t, quality=PageQuality.TEXT)
             for i, t in enumerate(texts)]
    ledger = PageLedger(material="fused", page_count=len(pages), pages=pages,
                        source_hash="t", parser_version="t")
    origin = []
    for i, (aid, label, local, src) in enumerate(origin_rows, start=1):
        origin.append({"artifact_id": aid, "label": label, "local_page": local,
                       "source_page": src, "global_page": i})
    return fusion.Universe(ledger=ledger, materials=[], offsets=offsets or {"a": 0, "b": 1},
                           origin=origin, pdf=Path("/dev/null"))


class RemapTests(unittest.TestCase):
    def test_range_crossing_materials_splits_with_source_pages(self):
        uni = _universe([("a", "高数.pdf", 1, 10), ("a", "高数.pdf", 2, 11),
                         ("b", "竞赛.pdf", 1, 5), ("b", "竞赛.pdf", 2, 6)],
                        ["t1", "t2", "t3", "t4"])
        refs = fusion._remap_ref(SourceRef(material="fused", page_start=2, page_end=3), uni)
        self.assertEqual([(r.material, r.page_start, r.page_end, r.source_page) for r in refs],
                         [("高数.pdf", 2, 2, 11), ("竞赛.pdf", 3, 3, 5)])

    def test_same_material_range_stays_one_ref(self):
        uni = _universe([("a", "高数.pdf", 1, 10), ("a", "高数.pdf", 2, 11)],
                        ["t1", "t2"])
        refs = fusion._remap_ref(SourceRef(material="fused", page_start=1, page_end=2), uni)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].page_end, 2)
        self.assertEqual(refs[0].source_page, 10)

    def test_remap_section_rewrites_blocks_and_section_refs(self):
        uni = _universe([("a", "高数.pdf", 1, 10), ("b", "竞赛.pdf", 1, 5)], ["t1", "t2"])
        sec = LectureSection(
            id="s", title="章",
            blocks=[{"id": "b1", "kind": "paragraph", "text": "内容在这里",
                     "source_refs": [{"material": "fused", "page_start": 1, "page_end": 2}]}],
            source_refs=[{"material": "fused", "page_start": 1, "page_end": 2}],
        )
        out = fusion.remap_section(sec, uni)
        self.assertEqual([r.material for r in out.blocks[0].source_refs], ["高数.pdf", "竞赛.pdf"])
        self.assertEqual([r.source_page for r in out.source_refs], [10, 5])


class DigestSectionTests(unittest.TestCase):
    def setUp(self) -> None:
        fusion.reset_registry()

    def test_every_page_is_cited_with_original_page_number(self):
        uni = _universe([("a", "高数.pdf", 1, 30), ("a", "高数.pdf", 2, 31),
                         ("b", "竞赛.pdf", 1, 7)],
                        ["第一页正文内容足够长可以成为一段。", "第二页正文内容。", "第三页正文。"],
                        offsets={"a": 0, "b": 2})
        chapter = fusion.Chapter(title="第一章 极限", spans=[
            fusion.MaterialSpan("a", "高数.pdf", [1, 2], [30, 31]),
            fusion.MaterialSpan("b", "竞赛.pdf", [1], [7]),
        ])
        sec = fusion.digest_section(chapter, uni, index=1)
        cited = [r.page_start for b in sec.blocks for r in b.source_refs]
        self.assertEqual(sorted(cited), [1, 2, 3])
        src_pages = [r.source_page for b in sec.blocks for r in b.source_refs]
        self.assertEqual(src_pages, [30, 31, 7])
        self.assertTrue(all(b.source_refs for b in sec.blocks))

    def test_transition_appears_when_material_changes(self):
        uni = _universe([("a", "高数.pdf", 1, 1), ("b", "竞赛.pdf", 1, 9)],
                        ["甲资料正文。", "乙资料正文。"])
        chapter = fusion.Chapter(title="第一章 极限", spans=[
            fusion.MaterialSpan("a", "高数.pdf", [1], [1]),
            fusion.MaterialSpan("b", "竞赛.pdf", [1], [9]),
        ])
        sec = fusion.digest_section(chapter, uni, index=1)
        self.assertIn("衔接", sec.blocks[1].text)
        self.assertIn("竞赛.pdf", sec.blocks[1].text)
        self.assertIn("第 9 页", sec.blocks[1].text)

    def test_duplicate_page_is_not_expanded_twice(self):
        body = ("函数在一点的极限存在当且仅当左右极限存在且相等，这是判断分段函数极限的关键步骤，"
                "也是很多同学一上来就套公式、结果把左右极限混在一起算错的地方；"
                "遇到分段点先分别求左右极限，再比较是否相等，最后才谈是否连续、是否可导；"
                "这一步写清楚，后面的导数定义和可导性判断就不会再凭感觉。")
        uni = _universe([("a", "高数.pdf", 1, 1), ("b", "竞赛.pdf", 1, 2)], [body, body])
        chapter = fusion.Chapter(title="第一章 极限", spans=[
            fusion.MaterialSpan("a", "高数.pdf", [1], [1]),
            fusion.MaterialSpan("b", "竞赛.pdf", [1], [2]),
        ])
        sec = fusion.digest_section(chapter, uni, index=1)
        self.assertTrue(chapter.deduped, "重复页必须被记录下来")
        self.assertIn("内容重复", sec.blocks[1].text)
        self.assertLess(len(sec.blocks[1].text), len(body))

    def test_blank_page_keeps_its_slot(self):
        uni = _universe([("a", "高数.pdf", 1, 1)], [""])
        chapter = fusion.Chapter(title="第一章", spans=[fusion.MaterialSpan("a", "高数.pdf", [1], [1])])
        sec = fusion.digest_section(chapter, uni, index=1)
        self.assertTrue(sec.blocks[0].source_refs)
        self.assertIn("扫描/图片页", sec.blocks[0].text)


if __name__ == "__main__":
    unittest.main()


class MathNormalizeTests(unittest.TestCase):
    """模型把“公式+说明”写在一个 formula 块里时，不能再套一层 $$。"""

    def _sec(self, text: str, kind: str = "formula") -> LectureSection:
        return LectureSection(id="s", title="温度特性", blocks=[
            {"id": "b1", "kind": kind, "text": text,
             "source_refs": [{"material": "m", "page_start": 1, "page_end": 1}]}],
            source_refs=[{"material": "m", "page_start": 1, "page_end": 1}])

    def test_mixed_formula_becomes_plain_paragraph(self):
        mixed = ("写成温度系数就是 $$ \\frac{\\Delta U_{BE}}{\\Delta T} \\approx -2.5 \\text{ mV/}^\\circ C $$ "
                 "即 $\\Delta U_{BE} = (-2.5) \\times \\Delta T$。")
        out = fusion._normalize_math(self._sec(mixed))
        block = out.blocks[0]
        self.assertEqual(block.kind.value, "paragraph")
        self.assertNotIn("\\frac", block.text)
        self.assertNotIn("$$", block.text)

    def test_single_formula_is_wrapped_once(self):
        out = fusion._normalize_math(self._sec("E = mc^2"))
        self.assertEqual(out.blocks[0].text, "$$E = mc^2$$")

    def test_already_wrapped_formula_untouched(self):
        out = fusion._normalize_math(self._sec("$$a^2 + b^2 = c^2$$"))
        self.assertEqual(out.blocks[0].text, "$$a^2 + b^2 = c^2$$")
        self.assertEqual(out.blocks[0].kind.value, "formula")


class RegistryIsolationTests(unittest.TestCase):
    def test_registries_do_not_leak_between_jobs(self):
        body = ("极限的四则运算法则要求参与运算的极限都存在才能拆开计算，否则会得出错误结论；"
                "遇到无穷大减无穷大、零乘无穷大这类未定式，必须先化成可以判断的形式，"
                "再决定用等价无穷小、夹逼还是洛必达。这一步是这一章最常见也最致命的失分点，"
                "做题时先写“两极限存在”，再动手拆项，能省掉一大半的返工时间。")
        a, b = fusion.DedupeRegistry(), fusion.DedupeRegistry()
        a.register(body, "第一章", 1)
        self.assertIsNotNone(a.find(body))
        self.assertIsNone(b.find(body), "另一份融合任务不应看到别处的登记表")


class SupportMetricTests(unittest.TestCase):
    """模型成文后要能报出“正文和引用页对不对得上”。"""

    def test_support_ratio_from_pages(self) -> None:
        uni = _universe([("a", "高数.pdf", 1, 1), ("a", "高数.pdf", 2, 2)],
                        ["函数在一点的极限存在要求左右极限相等",
                         "矩阵的秩等于非零子式的最高阶数"], offsets={"a": 0})
        sec = LectureSection(id="s", title="章", blocks=[
            {"id": "b1", "kind": "paragraph", "text": "极限存在要求左右极限相等，这是关键。",
             "source_refs": [{"material": "高数.pdf", "page_start": 1, "page_end": 1}]},
            {"id": "b2", "kind": "paragraph", "text": "天气很好适合出门散步和拍照留念。",
             "source_refs": [{"material": "高数.pdf", "page_start": 2, "page_end": 2}]},
        ], source_refs=[])
        got = fusion.measure_support(sec, uni)
        self.assertEqual(got["checked"], 2)
        self.assertEqual(got["supported"], 1)
        self.assertIn("b2", got["weak_blocks"])

    def test_figure_blocks_ignored(self) -> None:
        uni = _universe([("a", "A.pdf", 1, 1)], ["正文内容"], offsets={"a": 0})
        sec = LectureSection(id="s", title="章", blocks=[
            {"id": "f1", "kind": "figure", "text": "",
             "source_refs": [{"material": "A.pdf", "page_start": 1, "page_end": 1}]},
        ], source_refs=[])
        self.assertEqual(fusion.measure_support(sec, uni)["checked"], 0)


class TermRecallTests(unittest.TestCase):
    """成文章节要能算出“资料核心术语覆盖了多少”。"""

    def test_recall_counts_covered_terms(self) -> None:
        uni = _universe([("a", "高数.pdf", 1, 1)],
                        ["放大电路的静态工作点需要直流通路分析，三极管的放大系数决定放大能力。"
                         "放大电路的静态工作点需要直流通路分析。"], offsets={"a": 0})
        chapter = fusion.Chapter(title="章", spans=[fusion.MaterialSpan("a", "高数.pdf", [1], [1])])
        sec = LectureSection(id="s", title="章", blocks=[
            {"id": "b1", "kind": "paragraph", "text": "放大电路与三极管的关系要结合静态工作点看。"},
            {"id": "b2", "kind": "paragraph", "text": "这里完全没有涉及资料里的核心术语。"},
        ], source_refs=[])
        got = fusion.measure_term_recall(sec, chapter, uni)
        self.assertGreater(got["terms"], 0)
        self.assertGreaterEqual(got["recall"], 0.0)
        self.assertIn("recall", got)

    def test_empty_corpus_is_safe(self) -> None:
        uni = _universe([("a", "A.pdf", 1, 1)], [""], offsets={"a": 0})
        chapter = fusion.Chapter(title="章", spans=[fusion.MaterialSpan("a", "A.pdf", [1], [1])])
        sec = LectureSection(id="s", title="章", blocks=[])
        self.assertEqual(fusion.measure_term_recall(sec, chapter, uni)["recall"], 0.0)


class ProseSanitizeTests(unittest.TestCase):
    """摘要/结语里的 $...$ 不能原样进 PDF。"""

    def test_inline_math_removed(self) -> None:
        got = fusion.sanitize_prose("在 $A\\subset\\mathbb{R}^n$ 上讨论极限")
        self.assertNotIn("$", got)
        self.assertNotIn("\\", got)
        self.assertIn("讨论极限", got)

    def test_plain_text_untouched(self) -> None:
        text = "这段没有任何公式，应该原样保留。"
        self.assertEqual(fusion.sanitize_prose(text), text)


class ImprovementReasonTests(unittest.TestCase):
    """成文质量不达标要说明原因（用于重试提示），达标则沉默。"""

    def test_ok_is_empty(self) -> None:
        self.assertEqual(fusion.improvement_reason({"ratio": 0.9}, {"recall": 0.8}), "")

    def test_low_support_reported(self) -> None:
        reason = fusion.improvement_reason({"ratio": 0.3}, {"recall": 0.9})
        self.assertIn("支持率只有 30%", reason)

    def test_low_recall_lists_missing_terms(self) -> None:
        reason = fusion.improvement_reason({"ratio": 0.9},
                                           {"recall": 0.2, "missing": ["极限", "导数", "连续"]})
        self.assertIn("漏掉资料核心术语", reason)
        self.assertIn("极限", reason)

    def test_none_metrics_are_silent(self) -> None:
        self.assertEqual(fusion.improvement_reason({}, {}), "")


class RetryFlowTests(unittest.TestCase):
    """成文不达标时最多重试一次，且只有更好才采纳。"""

    def setUp(self) -> None:
        # 单页单块，避免 backfill 补文把指标抬到阈值线上，干扰重试判定
        self.uni = _universe([("a", "高数.pdf", 1, 1)],
                             ["函数在一点的极限存在要求左右极限相等，这是判断的关键。"],
                             offsets={"a": 0})
        self.chapter = fusion.Chapter(title="第一章", spans=[
            fusion.MaterialSpan("a", "高数.pdf", [1], [1])])

    def _sec(self, text: str) -> LectureSection:
        return LectureSection(id="s", title="第一章", blocks=[
            {"id": "b1", "kind": "paragraph", "text": text,
             "source_refs": [{"material": "高数.pdf", "page_start": 1, "page_end": 1}]}],
            source_refs=[{"material": "高数.pdf", "page_start": 1, "page_end": 1}])

    def test_retry_adopted_when_better(self) -> None:
        calls = {"n": 0}

        def fake(chapter, universe, client, **kwargs):
            calls["n"] += 1
            return self._sec("完全无关的天气讨论和穿衣建议。")

        outcome = fusion.author_with_retry(self.chapter, self.uni, object(),
                                           index=1, author_fn=fake)
        self.assertEqual(outcome["attempts"], 2)
        self.assertEqual(calls["n"], 2)
        self.assertIn("重试未变好", outcome["retry_reason"])

    def test_good_first_try_skips_retry(self) -> None:
        calls = {"n": 0}

        def fake(chapter, universe, client, **kwargs):
            calls["n"] += 1
            return self._sec("函数在一点的极限存在要求左右极限相等，这是判断的关键。")

        outcome = fusion.author_with_retry(self.chapter, self.uni, object(),
                                           index=1, author_fn=fake)
        self.assertEqual(outcome["attempts"], 1)
        self.assertEqual(calls["n"], 1)

    def test_retry_failure_keeps_first_and_reports(self) -> None:
        calls = {"n": 0}

        def fake(chapter, universe, client, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return self._sec("完全无关的天气讨论。")
            raise RuntimeError("模型超时")

        outcome = fusion.author_with_retry(self.chapter, self.uni, object(),
                                           index=1, author_fn=fake)
        self.assertEqual(outcome["attempts"], 1)
        self.assertIn("重试失败", outcome["retry_reason"])
        self.assertTrue(outcome["section"].blocks)
