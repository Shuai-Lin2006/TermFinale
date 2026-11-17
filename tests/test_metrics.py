"""质量指标纯函数：重复句、模板句、术语召回、引用支持。"""
from __future__ import annotations

import unittest

from tfv2.quality import metrics as M


class SentenceMetricTests(unittest.TestCase):
    def test_dup_ratio(self) -> None:
        self.assertAlmostEqual(M.dup_sentence_ratio(["a" * 10, "b" * 10]), 0.0)
        self.assertAlmostEqual(M.dup_sentence_ratio(["a" * 10, "a" * 10]), 0.5)
        self.assertAlmostEqual(M.dup_sentence_ratio([]), 0.0)

    def test_boilerplate_detects_repeats(self) -> None:
        repeated = "三极管放大电路" * 40
        self.assertGreater(M.boilerplate_per_1k(repeated), 500)
        varied = "".join(f"{chr(0x4e00 + i)}{chr(0x4e00 + i + 100)}" for i in range(40))
        self.assertLess(M.boilerplate_per_1k(varied), 100)


class TermMetricTests(unittest.TestCase):
    CORPUS = ("放大电路的静态工作点需要直流通路来分析，三极管的电流放大系数决定放大能力；"
              "温度升高会让反向饱和电流增大，" * 5)

    def test_candidates_contain_core_terms(self) -> None:
        terms = M.term_candidates(self.CORPUS, top=20)
        joined = "|".join(terms)
        self.assertTrue(any(t in joined for t in ("放大电路", "三极管", "静态工作点")), terms)

    def test_recall_hit_and_missing(self) -> None:
        got = M.term_recall(["放大电路", "三极管", "不存在术"], "放大电路里三极管的放大系数")
        self.assertEqual(got["terms"], 3)
        self.assertEqual(got["hit"], 2)
        self.assertAlmostEqual(got["recall"], 0.667, places=3)
        self.assertEqual(got["missing"], ["不存在术"])

    def test_empty_terms(self) -> None:
        self.assertEqual(M.term_recall([], "x")["recall"], 0.0)


class CitationSupportTests(unittest.TestCase):
    PAGES = {
        1: "放大电路的静态工作点需要先画直流通路，再列输入回路方程与输出回路方程求解。",
        2: "三极管的电流放大系数体现放大能力，β 过大时稳定性会变差。",
    }

    def _block(self, text: str, page: int, bid: str) -> dict:
        return {"id": bid, "kind": "paragraph", "text": text,
                "source_refs": [{"page_start": page, "page_end": page}]}

    def test_supported_and_weak(self) -> None:
        blocks = [self._block("静态工作点要先画直流通路再列方程求解", 1, "b1"),
                  self._block("完全无关的天气讨论与穿衣建议内容", 2, "b2")]
        got = M.citation_support(blocks, lambda p: self.PAGES.get(p, ""))
        self.assertEqual(got["checked"], 2)
        self.assertEqual(got["supported"], 1)
        self.assertIn("b2", got["weak_blocks"])

    def test_figures_skipped(self) -> None:
        blocks = [{"id": "f", "kind": "figure", "text": "", "source_refs": [{"page_start": 1}]}]
        self.assertEqual(M.citation_support(blocks, lambda p: "")["checked"], 0)


if __name__ == "__main__":
    unittest.main()


class MathSanitizeTests(unittest.TestCase):
    """公式/TeX 收口：这是“内容体检未通过”的高频根因。"""

    def _sec(self, kind, text):
        from tfv2.domain.lecture import LectureSection
        return LectureSection(id="s", title="章", blocks=[
            {"id": "b1", "kind": kind, "text": text,
             "source_refs": [{"material": "m.pdf", "page_start": 1, "page_end": 1}]}],
            source_refs=[{"material": "m.pdf", "page_start": 1, "page_end": 1}])

    def test_paragraph_tex_becomes_plain(self) -> None:
        from tfv2.authoring.normalize import sanitize_section_math
        sec = self._sec("paragraph", "输出电阻为 R_{\\mathrm{o}} = R_c ∥ R_L")
        got = sanitize_section_math(sec)
        self.assertNotIn("\\", got.blocks[0].text)
        self.assertNotIn("$", got.blocks[0].text)

    def test_mixed_formula_block_becomes_paragraph(self) -> None:
        from tfv2.authoring.normalize import sanitize_section_math
        sec = self._sec("formula", "$$共集电极电路的输出电阻为\n$$r_{\\mathrm{o}} = R_c$$")
        got = sanitize_section_math(sec)
        self.assertEqual(got.blocks[0].kind.value, "paragraph")
        self.assertNotIn("$", got.blocks[0].text)

    def test_mixed_dollar_formula_degrades(self) -> None:
        from tfv2.authoring.normalize import sanitize_section_math
        sec = self._sec("formula", "$$$I_{BQ} = \\frac{U_{CC} - U_{BE}}{R_b}$，$I_{CQ} = \\beta I_{BQ}$（含发射极")
        got = sanitize_section_math(sec)
        self.assertEqual(got.blocks[0].kind.value, "paragraph")
        self.assertNotIn("$", got.blocks[0].text)

    def test_truncated_formula_degrades(self) -> None:
        from tfv2.authoring.normalize import sanitize_section_math
        sec = self._sec("formula", "$$r_{be} = r_{bb'} + (1 + \\beta) \\frac{26 \\text{mV")
        got = sanitize_section_math(sec)
        self.assertEqual(got.blocks[0].kind.value, "paragraph", "括号不闭合的公式会让 KaTeX 失败")

    def test_cjk_formula_degrades(self) -> None:
        from tfv2.authoring.normalize import sanitize_section_math
        sec = self._sec("formula", "$$U_{CEQ} = U_{CC} - I_{CQ} R_c 时的工作点$$")
        got = sanitize_section_math(sec)
        self.assertEqual(got.blocks[0].kind.value, "paragraph")

    def test_clean_formula_kept(self) -> None:
        from tfv2.authoring.normalize import sanitize_section_math
        sec = self._sec("formula", "r_o = R_c")
        got = sanitize_section_math(sec)
        self.assertEqual(got.blocks[0].kind.value, "formula")
        self.assertEqual(got.blocks[0].text, "$$r_o = R_c$$")


class HeadingRecallTests(unittest.TestCase):
    """资料目录覆盖：结构一致性指标（无需标注）。"""

    def test_matches_with_numbering_noise(self) -> None:
        got = M.heading_recall(["1.3.4 三极管的特性曲线", "第二章 放大电路"], "第一章 三极管的特性曲线与放大电路基础")
        self.assertEqual(got["hit"], 2)
        self.assertEqual(got["recall"], 1.0)

    def test_missing_reported(self) -> None:
        got = M.heading_recall(["三极管的特性曲线", "反馈放大电路"], "只讲了三极管的特性曲线")
        self.assertEqual(got["hit"], 1)
        self.assertEqual(got["missing"], ["反馈放大电路"])

    def test_empty_headings(self) -> None:
        self.assertEqual(M.heading_recall([], "任意")["recall"], 0.0)
        self.assertEqual(M.heading_recall([""], "任意")["recall"], 0.0)


class InlineMathTests(unittest.TestCase):
    """数学书：能渲染的行内公式要保留，不能的才纯文本化。"""

    def _sec(self, text):
        from tfv2.domain.lecture import LectureSection
        return LectureSection(id="s", title="章", blocks=[
            {"id": "b1", "kind": "paragraph", "text": text,
             "source_refs": [{"material": "m", "page_start": 1, "page_end": 1}]}],
            source_refs=[{"material": "m", "page_start": 1, "page_end": 1}])

    def test_valid_inline_kept(self) -> None:
        from tfv2.authoring.normalize import sanitize_section_math
        text = "由 $f(x) = x^2$ 可得极限为 $0$，这里用到了连续函数的性质。"
        got = sanitize_section_math(self._sec(text)).blocks[0].text
        self.assertEqual(got, text, "可渲染的行内公式应保留")

    def test_stray_tex_outside_math_cleaned(self) -> None:
        from tfv2.authoring.normalize import sanitize_section_math
        text = "这里用 \\\\alpha 表示系数，且 $x>0$。"
        got = sanitize_section_math(self._sec(text)).blocks[0].text
        self.assertNotIn("\\\\", got)

    def test_unbalanced_dollar_cleaned(self) -> None:
        from tfv2.authoring.normalize import sanitize_section_math
        got = sanitize_section_math(self._sec("若 $x>0 则成立，注意这里少一个美元符号。")).blocks[0].text
        self.assertNotIn("$", got)


class SentenceDedupeTests(unittest.TestCase):
    """模型偶尔把一句话写两遍：同节内去重，跨节不去重。"""

    def _sec(self, *texts):
        from tfv2.domain.lecture import LectureSection
        return LectureSection(id="s", title="章", blocks=[
            {"id": f"b{i}", "kind": "paragraph", "text": t,
             "source_refs": [{"material": "m", "page_start": 1, "page_end": 1}]}
            for i, t in enumerate(texts)],
            source_refs=[{"material": "m", "page_start": 1, "page_end": 1}])

    def test_duplicate_sentence_removed(self) -> None:
        from tfv2.authoring.normalize import dedupe_section_sentences
        got = dedupe_section_sentences(self._sec(
            "极限存在要求左右极限相等。这是判断极限的关键。",
            "极限存在要求左右极限相等。再补一句不同的话。")),
        blocks = [b.text for b in got[0].blocks]
        joined = "".join(blocks)
        self.assertEqual(joined.count("极限存在要求左右极限相等"), 1, blocks)

    def test_distinct_sentences_kept(self) -> None:
        from tfv2.authoring.normalize import dedupe_section_sentences
        got = dedupe_section_sentences(self._sec("第一句不同的话。第二句也不同。"))
        self.assertIn("第一句不同的话", got.blocks[0].text)


class StrayBackslashTests(unittest.TestCase):
    """OCR 里的 \\( \\; 这类反斜杠必须清掉，否则 PDF 门禁判“公式块外有 TeX”。"""

    def test_inline_delimiters_removed(self) -> None:
        from tfv2.authoring.normalize import _plain_math
        got = _plain_math("C=\\(x,y,z) 且 f\\; x")
        self.assertNotIn("\\", got)

    def test_formula_with_latex_delimiters_degrades(self) -> None:
        from tfv2.authoring.normalize import _formula_problem
        self.assertEqual(_formula_problem("\\(x,y,z)"), "latex-delimiters")
