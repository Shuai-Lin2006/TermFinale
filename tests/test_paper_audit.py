"""整卷体检：题型完整、题量、分值、答案、总分（确定性，不调模型）。"""
from __future__ import annotations

import unittest

from tfv2.product.exam import audit_paper


def _q(score: float, answer=0, qtype: str = "choice") -> dict:
    return {"qtype": qtype, "stem": "题干", "options": ["A", "B", "C", "D"],
            "answer": answer, "answer_text": "A", "score": score, "source_page": 1}


def _paper(*sections) -> dict:
    return {"title": "测试卷", "sections": list(sections)}


class PaperAuditTests(unittest.TestCase):
    def test_complete_paper_is_validated(self) -> None:
        bp = _paper({"name": "一、选择题", "type": "choice", "count": 2, "score": 40,
                     "questions": [_q(20), _q(20)]},
                    {"name": "二、计算题", "type": "calculation", "count": 1, "score": 60,
                     "questions": [_q(60, qtype="calculation")]})
        got = audit_paper(bp, audit={"checked": True, "conflicts": []})
        self.assertEqual(got["issues"], [])
        self.assertEqual(got["total_score"], 100.0)
        self.assertEqual(got["status"], "validated")

    def test_missing_questions_rejected(self) -> None:
        bp = _paper({"name": "一、选择题", "type": "choice", "count": 3, "score": 100,
                     "questions": [_q(50), _q(50)]})
        got = audit_paper(bp)
        self.assertIn("一、选择题 题量 2/3", got["issues"])
        self.assertEqual(got["status"], "rejected")

    def test_section_score_mismatch_rejected(self) -> None:
        bp = _paper({"name": "一、选择题", "type": "choice", "count": 2, "score": 40,
                     "questions": [_q(20), _q(10)]},
                    {"name": "二、简答题", "type": "short_answer", "count": 1, "score": 60,
                     "questions": [_q(60, qtype="short_answer")]})
        got = audit_paper(bp)
        self.assertTrue(any("分值 30.0 与蓝图 40.0 不一致" in x for x in got["issues"]), got["issues"])

    def test_total_not_100_rejected(self) -> None:
        bp = _paper({"name": "一、选择题", "type": "choice", "count": 2, "score": 100,
                     "questions": [_q(40), _q(50)]})
        got = audit_paper(bp)
        self.assertEqual(got["total_score"], 90.0)
        self.assertIn("总分不是 100：90.0", got["issues"])
        self.assertEqual(got["status"], "rejected")

    def test_missing_answer_and_zero_score_flagged(self) -> None:
        bp = _paper({"name": "一、填空题", "type": "fill_blank", "count": 2, "score": 100,
                     "questions": [{"qtype": "fill_blank", "stem": "填空1", "answer": None, "score": 50},
                                   {"qtype": "fill_blank", "stem": "填空2", "answer": "x", "score": 0}]})
        got = audit_paper(bp)
        self.assertIn("一、填空题 第 1 题没有答案", got["issues"])
        self.assertTrue(any("分值不大于 0" in x for x in got["issues"]))

    def test_fill_blank_answer_text_counts_as_answered(self) -> None:
        """填空题的答案在 answer_text 里，answer 为 None 是设计而非缺答案。"""
        bp = _paper({"name": "一、填空题", "type": "fill_blank", "count": 2, "score": 100,
                     "questions": [{"qtype": "fill_blank", "stem": "填空1", "answer": None,
                                    "answer_text": "1.62 μA", "score": 50},
                                   {"qtype": "fill_blank", "stem": "填空2", "answer": None,
                                    "answer_text": "3.20 mA", "score": 50}]})
        got = audit_paper(bp, audit={"checked": True, "conflicts": []})
        self.assertEqual(got["issues"], [])
        self.assertEqual(got["status"], "validated")

    def test_choice_answer_out_of_range_flagged(self) -> None:
        bp = _paper({"name": "一、选择题", "type": "choice", "count": 1, "score": 100,
                     "questions": [{"qtype": "choice", "stem": "题", "options": ["A", "B", "C", "D"],
                                    "answer": 7, "score": 100}]})
        self.assertIn("一、选择题 第 1 题答案不在 0–3", audit_paper(bp)["issues"])

    def test_unchecked_audit_is_review_not_validated(self) -> None:
        bp = _paper({"name": "一、选择题", "type": "choice", "count": 1, "score": 100,
                     "questions": [_q(100)]})
        got = audit_paper(bp, audit={"checked": False, "conflicts": []})
        self.assertEqual(got["status"], "review")

    def test_conflicts_block_validation(self) -> None:
        bp = _paper({"name": "一、选择题", "type": "choice", "count": 1, "score": 100,
                     "questions": [_q(100)]})
        got = audit_paper(bp, audit={"checked": True, "conflicts": [{"no": 1}]})
        self.assertEqual(got["status"], "rejected")
        self.assertIn("答案审计仍有 1 处冲突", got["issues"])

    def test_empty_paper_rejected(self) -> None:
        got = audit_paper({"sections": []})
        self.assertIn("试卷没有任何题型", got["issues"])
        self.assertEqual(got["status"], "rejected")


if __name__ == "__main__":
    unittest.main()


class BlueprintParseTests(unittest.TestCase):
    """用户自定义蓝图必须照做，不能只当 prompt 里的参考。"""

    def test_simple_blueprint_parsed(self) -> None:
        from tfv2.product.exam import parse_blueprint_text
        got = parse_blueprint_text("选择题 2 题 50 分；填空题 2 题 50 分")
        self.assertEqual([(x["type"], x["count"], x["score"]) for x in got],
                         [("choice", 2, 50), ("fill_blank", 2, 50)])

    def test_numbered_blueprint_parsed(self) -> None:
        from tfv2.product.exam import parse_blueprint_text
        got = parse_blueprint_text("一、选择题 10 题 30 分；二、计算题 4 题 40 分；三、简答题 2 题 30 分")
        self.assertEqual([x["type"] for x in got], ["choice", "calculation", "short_answer"])
        self.assertEqual(sum(x["score"] for x in got), 100)

    def test_unparseable_returns_empty(self) -> None:
        from tfv2.product.exam import parse_blueprint_text
        self.assertEqual(parse_blueprint_text("按老师要求随便出一点"), [])
        self.assertEqual(parse_blueprint_text("选择题 0 题 0 分"), [])

    def test_blueprint_skips_model_call(self) -> None:
        from tfv2.product.exam import _blueprint

        class Boom:
            def json(self, *a, **k):
                raise AssertionError("用户蓝图能解析时不应再让模型重新设计")

        bp = _blueprint(Boom(), subject="电子技术", types=["choice"], difficulty=3,
                        reference="", user_blueprint="选择题 8 题 40 分；填空题 6 题 20 分；计算题 2 题 40 分",
                        mode="mock")
        self.assertTrue(bp.get("user_blueprint"))
        self.assertEqual([(s["type"], s["count"]) for s in bp["sections"]],
                         [("choice", 8), ("fill_blank", 6), ("calculation", 2)])
        self.assertEqual(sum(s["score"] for s in bp["sections"]), 100)

    def test_too_small_blueprint_is_refused_with_reason(self) -> None:
        from tfv2.product.exam import ExamError, _blueprint

        class Boom:
            def json(self, *a, **k):
                raise AssertionError("不应调用模型")

        with self.assertRaises(ExamError) as ctx:
            _blueprint(Boom(), subject="电子技术", types=["choice"], difficulty=3,
                       reference="", user_blueprint="选择题 2 题 50 分；填空题 2 题 50 分", mode="mock")
        self.assertIn("题量过少", str(ctx.exception))


class ExamCoverageFloorTests(unittest.TestCase):
    """按蓝图出小卷时，页覆盖目标要按题量封顶，不能拿做不到的指标卡交付。"""

    def _doc(self, total_questions: int, cited: int, pages: int = 60, source: str = "user") -> dict:
        """total_questions 是蓝图题量，cited 是这些题实际覆盖到的页数。"""
        qs = [{"qtype": "choice", "stem": f"第{i}题：三极管工作在放大区时的参数变化与判断方法",
               "options": ["A", "B", "C", "D"], "answer": 0, "answer_text": "A",
               "analysis": "按资料第 i 页给出的条件逐步推导即可得出结论",
               "source_page": i + 1, "score": round(100 / total_questions, 1)}
              for i in range(cited)]
        return {"coverage": {"pages": list(range(1, pages + 1))},
                "content": {"blueprint_source": source,
                            "sections": [{"name": "一、选择题", "count": total_questions,
                                          "score": round(sum(q["score"] for q in qs), 1),
                                          "questions": qs}]}}

    def test_small_blueprint_is_not_penalised(self) -> None:
        from tfv2.quality.trust import audit_exam
        got = audit_exam(self._doc(total_questions=12, cited=12))
        self.assertFalse([x for x in got["issues"] if "页覆盖" in x], got["issues"])

    def test_real_page_gap_is_still_reported(self) -> None:
        from tfv2.quality.trust import audit_exam
        got = audit_exam(self._doc(total_questions=40, cited=6))
        self.assertTrue([x for x in got["issues"] if "页覆盖" in x], got["issues"])

    def test_default_blueprint_keeps_strict_floor(self) -> None:
        from tfv2.quality.trust import audit_exam
        got = audit_exam(self._doc(total_questions=12, cited=12, source="default"))
        self.assertTrue([x for x in got["issues"] if "页覆盖" in x], got["issues"])


class UserBlueprintDeliveryTests(unittest.TestCase):
    """用户按蓝图出的小卷：页覆盖只作提示，不能把整卷降成 partial。"""

    _STEMS = [
        "共射放大电路里，静态工作点为什么必须落在放大区？给出判断步骤。",
        "三极管的输入特性曲线为什么会出现死区？工程上怎么处理？",
        "输出特性曲线分成哪三个区？各自对应什么工作状态？",
        "β 与 α 的物理含义不同，它们之间是什么关系？用公式说明。",
        "温度升高时，三极管的哪几个参数会变化？分别朝哪个方向变？",
        "反向饱和电流由什么载流子形成？为什么它随温度迅速增大？",
        "穿透电流与集电极-发射极漏电流是什么关系？",
        "共基极接法下，集电结与发射结的偏置分别是什么状态？",
        "共发射极接法下，发射结与集电结的偏置分别是什么状态？",
        "饱和压降为什么不能忽略？它影响什么电路指标？",
        "最大集电极功耗的含义是什么？超出会怎样？",
        "热击穿的物理过程是什么？为什么与散热条件有关？",
    ]

    def _doc(self, source: str, cited: int, questions: int = 12) -> dict:
        """questions 题、只落在 cited 个不同页上（模拟题目共用资料页）。"""
        scores = [round(100 / questions, 1)] * (questions - 1)
        scores.append(round(100 - sum(scores), 1))
        qs = []
        for i in range(questions):
            qs.append({"qtype": "fill_blank",
                       "stem": self._STEMS[i % len(self._STEMS)],
                       "answer": None, "answer_text": "略",
                       "analysis": "依据资料原文推导",
                       "source_page": (i % cited) + 1, "score": scores[i]})
        return {"kind": "exam", "status": "validated", "issues": [],
                "coverage": {"pages": list(range(1, 61)), "pages_cited": [q["source_page"] for q in qs]},
                "content": {"blueprint_source": source,
                            "sections": [{"name": "一、填空题", "count": questions,
                                          "score": round(sum(q["score"] for q in qs), 1),
                                          "questions": qs}],
                            "total_score": 100,
                            "answer_audit": {"checked": True, "conflicts": []}}}

    def test_user_blueprint_stays_validated(self) -> None:
        from tfv2.product import delivery
        out = delivery.apply_exam_delivery(self._doc("user", cited=8, questions=12))
        self.assertEqual(out["status"], "validated")
        self.assertTrue(any("页覆盖" in w for w in out.get("warnings") or []))

    def test_default_blueprint_with_short_coverage_is_partial(self) -> None:
        from tfv2.product import delivery
        out = delivery.apply_exam_delivery(self._doc("default", cited=8, questions=12))
        self.assertEqual(out["status"], "partial")


class TopUpSectionTests(unittest.TestCase):
    """题型没凑够时补一轮；补不上就如实留缺口，不能伪造。"""

    def _bp(self, have: int, want: int) -> dict:
        qs = [{"qtype": "choice", "stem": f"已有很多不同的题目内容第{i}号用于占位与区分",
               "options": ["A", "B", "C", "D"], "answer": 0, "answer_text": "A",
               "analysis": "解析内容", "source_page": i + 1, "score": 50 / want} for i in range(have)]
        return {"title": "t", "sections": [{"name": "一、选择题", "type": "choice",
                                           "count": want, "score": 50, "questions": qs}]}

    def _q(self, page: int, stem: str) -> dict:
        return {"qtype": "choice", "stem": stem, "options": ["A", "B", "C", "D"], "answer": 1,
                "answer_text": "B", "analysis": "因为条件满足所以选 B", "source_page": page,
                "source_no": "补充"}

    def test_fills_missing_questions_and_realigns_scores(self) -> None:
        from tfv2.product.exam import _top_up_sections

        class Client:
            def json(self, system, user, **kwargs):
                return {"questions": [self.q1]}

        client = Client()
        client.q1 = self._q(2, "补上的第一道题：分析给定的偏置电路并判断工作状态")
        bp = self._bp(have=1, want=2)
        got = _top_up_sections(bp, [1, 2, 3], {1: "页1", 2: "页2", 3: "页3"}, "mock", "其他", {},
                               client)
        self.assertEqual(got["filled"], 1)
        sec = bp["sections"][0]
        self.assertEqual(sec["count"], 2)
        self.assertAlmostEqual(sum(q["score"] for q in sec["questions"]), 50.0, places=1)

    def test_duplicate_stem_not_added(self) -> None:
        from tfv2.product.exam import _top_up_sections
        bp = self._bp(have=1, want=2)
        stem = bp["sections"][0]["questions"][0]["stem"]

        class Client:
            def json(self, system, user, **kwargs):
                return {"questions": [{"qtype": "choice", "stem": stem, "options": ["A", "B", "C", "D"],
                                       "answer": 0, "answer_text": "A", "analysis": "解析内容",
                                       "source_page": 1}]}

        got = _top_up_sections(bp, [1, 2, 3], {1: "页1"}, "mock", "其他", {}, Client())
        self.assertEqual(got["filled"], 0)
        self.assertEqual(len(bp["sections"][0]["questions"]), 1)

    def test_full_section_skips_model_call(self) -> None:
        from tfv2.product.exam import _top_up_sections

        class Boom:
            def json(self, *a, **k):
                raise AssertionError("题量已够不应再调模型")

        bp = self._bp(have=2, want=2)
        got = _top_up_sections(bp, [1, 2], {1: "p", 2: "p"}, "mock", "其他", {}, Boom())
        self.assertEqual(got["filled"], 0)

    def test_invalid_question_leaves_gap(self) -> None:
        from tfv2.product.exam import _top_up_sections

        class Client:
            def json(self, system, user, **kwargs):
                # 缺页码 → _parse_question 直接拒绝
                return {"questions": [{"qtype": "choice", "stem": "没有有效页码的题目内容足够长",
                                       "options": ["A", "B", "C", "D"], "answer": 0,
                                       "analysis": "解析内容", "source_page": 99}]}

        bp = self._bp(have=1, want=2)
        got = _top_up_sections(bp, [1, 2], {1: "p", 2: "p"}, "mock", "其他", {}, Client())
        self.assertEqual(got["filled"], 0)
        self.assertEqual(bp["sections"][0]["count"], 2)


class ExamPreconditionTests(unittest.TestCase):
    """没有讲义结构的资料出卷，要给明确原因，不能抛 FileNotFoundError。"""

    def test_missing_sections_raises_exam_error(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from tfv2.product import exam

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "source_pages.json").write_text('{"page_count": 1, "pages": [{"page": 1, "text": "x"}]}',
                                                    encoding="utf-8")
            with patch.object(exam.service, "artifact_path", return_value=root), \
                    patch.object(exam.service, "get_artifact", return_value={}):
                with self.assertRaises(exam.ExamError) as ctx:
                    exam.run_exam("aid", mode="mock", subject="其他", client=object())
            self.assertIn("sections.json", str(ctx.exception))


class ReferenceGuardTests(unittest.TestCase):
    """非题目文件必须拦在门口；真题结构解析失败必须留痕。"""

    EXAM_TEXT = """一、选择题
1. 极限存在的条件是（ ）
A. 左极限存在 B. 右极限存在 C. 左右极限存在且相等 D. 以上都不对
答案：C
2. 下列函数在 x=0 处连续的是（ ）
A. 1/x B. |x| C. tan x D. ln x
答案：B
二、填空题
3. 函数极限的定义中，ε 与 δ 的关系是 ____。
参考答案：对任意 ε>0，存在 δ>0
"""

    LECTURE_TEXT = """第一章 极限与连续
1. 极限的直观含义
函数趋近于某点时，函数值趋近于某个常数，这个常数就是极限。
2. 极限的运算法则
四则运算要求两个极限都存在才能拆分，否则会得出错误结论。
3. 夹逼准则
"""

    def test_exam_paper_recognised(self) -> None:
        from tfv2.product.exam import looks_like_question_paper
        shape = looks_like_question_paper(self.EXAM_TEXT)
        self.assertTrue(shape["looks"], shape)
        self.assertGreaterEqual(shape["qnum"], 3)

    def test_lecture_is_not_a_question_paper(self) -> None:
        from tfv2.product.exam import looks_like_question_paper
        shape = looks_like_question_paper(self.LECTURE_TEXT)
        self.assertFalse(shape["looks"], shape)
        self.assertIn("不构成题目卷特征", shape["reason"])

    def test_guard_blocks_lecture_without_llm(self) -> None:
        from tfv2.product.exam import reference_guard
        reason = reference_guard(self.LECTURE_TEXT, {"items": [{"no": "1"}]})
        self.assertIsNotNone(reason)
        self.assertIn("不会静默把非题目文件当结构参考", reason)
        self.assertIsNone(reference_guard(self.LECTURE_TEXT, {"items": [{"no": "1"}]},
                                          allow_non_question=True))

    def test_guard_allows_real_exam(self) -> None:
        from tfv2.product.exam import reference_guard
        self.assertIsNone(reference_guard(self.EXAM_TEXT, {"items": [{"no": "1"}, {"no": "2"}]}))

    def test_bank_marks_non_question_as_unused(self) -> None:
        from tfv2.product.exam import _reference_bank

        class Boom:
            def json(self, *a, **k):
                raise AssertionError("非题目文本不应再花一次模型调用")

        bank = _reference_bank(Boom(), self.LECTURE_TEXT)
        self.assertEqual(bank["items"], [])
        self.assertFalse(bank["used"])
        self.assertIn("不构成题目卷特征", bank["reason"])

    def test_reference_structure_failure_is_recorded(self) -> None:
        from tfv2.product.exam import _blueprint

        class Client:
            def json(self, *a, **k):
                raise RuntimeError("模型返回不完整")

        bp = _blueprint(Client(), subject="其他", types=["choice"], difficulty=3,
                        reference="一、选择题\n1. 题\nA. x B. y\n答案：A", user_blueprint="",
                        mode="mock")
        self.assertFalse(bp.get("reference_structure"))
        self.assertIn("模型返回不完整", bp.get("reference_structure_error") or "")


class ReferenceRealPdfTests(unittest.TestCase):
    """用真实 PDF 形状验证：讲义拦住、题卷放行（不调模型）。"""

    def _lecture_like_pdf(self, path) -> None:
        import pymupdf
        doc = pymupdf.open()
        page = doc.new_page()
        lines = ["第一章 极限与连续", "1. 极限的直观含义", "函数趋近某点时，函数值趋近某常数，这就是极限。",
                 "2. 极限的运算法则", "两个极限都存在时才能拆开计算，否则结论错误。",
                 "3. 夹逼准则", "用两个已知极限夹住目标函数，从而求出目标极限。"]
        y = 80
        for line in lines:
            page.insert_text((60, y), line, fontsize=12, fontname="china-s")
            y += 24
        doc.save(str(path))
        doc.close()

    def test_lecture_pdf_is_rejected_by_text(self) -> None:
        import tempfile
        from pathlib import Path
        from tfv2.product.exam import _pdf_text, looks_like_question_paper, reference_guard

        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "lecture.pdf"
            self._lecture_like_pdf(pdf)
            text = _pdf_text(pdf)
            shape = looks_like_question_paper(text)
            self.assertFalse(shape["looks"], shape)
            reason = reference_guard(text, {"items": [{"no": "1"}]})
            self.assertIsNotNone(reason)
            self.assertIn("不会静默把非题目文件当结构参考", reason)


class ReferenceStructureTests(unittest.TestCase):
    """真题结构还原：确定性解析 + 与模型结果比对的可量化指标。"""

    REAL_LINES = ("一、单项选择题(每小题3分,共18分)\n"
                  "二、填空题(每小题3分,共18分)\n"
                  "三、计算题(每小题7分,共28分)\n"
                  "五、证明题与应用题(每小题9分,共18分)")

    def test_deterministic_parse_from_real_headers(self) -> None:
        from tfv2.product.exam import parse_sections_deterministic
        rows = parse_sections_deterministic(self.REAL_LINES)
        self.assertEqual([r["type"] for r in rows], ["choice", "fill_blank", "calculation", "proof"])
        self.assertEqual([r["count"] for r in rows], [6, 6, 4, 2])
        self.assertEqual(sum(r["score"] for r in rows), 82, "真题里只有 82 分可见，缺的分不该被编出来")

    def test_fidelity_ok_and_not_ok(self) -> None:
        from tfv2.product.exam import parse_sections_deterministic, structure_fidelity
        det = parse_sections_deterministic(self.REAL_LINES)
        good = structure_fidelity([dict(x) for x in det], det)
        self.assertTrue(good["ok"], good)
        bad = structure_fidelity([dict(det[0])], det)
        self.assertFalse(bad["ok"])
        self.assertLess(bad["type_recall"], 0.99)

    def test_blueprint_records_fidelity(self) -> None:
        from tfv2.product.exam import _blueprint

        class Client:
            def json(self, system, user, **kw):
                return {"sections": [
                    {"name": "一、单项选择题", "type": "choice", "count": 6, "score": 18},
                    {"name": "二、填空题", "type": "fill_blank", "count": 6, "score": 18},
                    {"name": "三、计算题", "type": "calculation", "count": 4, "score": 28},
                    {"name": "五、证明题", "type": "proof", "count": 2, "score": 18},
                    {"name": "六、其他", "type": "other", "count": 3, "score": 18},
                ]}

        bp = _blueprint(Client(), subject="其他", types=["choice"], difficulty=3,
                        reference=self.REAL_LINES, user_blueprint="", mode="mock")
        self.assertTrue(bp["reference_structure"])
        fidelity = bp.get("reference_fidelity") or {}
        self.assertIn("type_recall", fidelity)
        self.assertGreater(fidelity["type_recall"], 0.9)

    def test_no_headers_means_no_fidelity(self) -> None:
        from tfv2.product.exam import parse_sections_deterministic
        self.assertEqual(parse_sections_deterministic("随便一段讲义正文，没有题型标题。"), [])


class StructureFormatVariantsTests(unittest.TestCase):
    def test_ben_question_format(self) -> None:
        from tfv2.product.exam import parse_sections_deterministic
        text = ("一、(本题30分,每小题6分)\n二、（本题14分）解方程\n"
                "三、(本题14分)设曲面\n四、(本题14分)\n五、(本题 14 分) 设 f(x)\n六、(本题 14分）")
        rows = parse_sections_deterministic(text)
        self.assertEqual(len(rows), 6, rows)
        self.assertEqual(sum(r["score"] for r in rows), 100)
        self.assertEqual(rows[0]["count"], 5, "30 分 / 每题 6 分 = 5 题")


class QuestionPagePlanTests(unittest.TestCase):
    """出卷页码规划：一题一页、尽量铺开、题多时才复用。"""

    def _sections(self, *counts) -> list[dict]:
        return [{"name": f"题型{i+1}", "count": c, "score": 100 // len(counts)}
                for i, c in enumerate(counts)]

    def test_distinct_and_spread_when_enough_pages(self) -> None:
        from tfv2.product.exam import plan_question_pages
        secs = self._sections(3, 3)
        plan = plan_question_pages(secs, list(range(1, 101)))
        flat = [p for group in plan for p in group]
        self.assertEqual(len(flat), 6)
        self.assertEqual(len(set(flat)), 6, "题量不超过页数时必须一题一页")
        self.assertGreater(max(flat) - min(flat), 50, "不能全挤在开头")
        self.assertEqual([len(g) for g in plan], [3, 3], "题量按题型分配")

    def test_all_pages_used_when_questions_equal_pages(self) -> None:
        from tfv2.product.exam import plan_question_pages
        secs = self._sections(4, 4)
        plan = plan_question_pages(secs, list(range(1, 9)))
        flat = sorted(p for group in plan for p in group)
        self.assertEqual(flat, list(range(1, 9)))

    def test_reuse_only_when_questions_exceed_pages(self) -> None:
        from tfv2.product.exam import plan_question_pages
        secs = self._sections(3, 3)
        plan = plan_question_pages(secs, [1, 2, 3])
        flat = [p for group in plan for p in group]
        self.assertEqual(len(flat), 6)
        self.assertEqual(set(flat), {1, 2, 3})
        self.assertTrue(all(flat.count(p) == 2 for p in (1, 2, 3)))

    def test_empty_inputs_are_safe(self) -> None:
        from tfv2.product.exam import plan_question_pages
        self.assertEqual(plan_question_pages([], [1, 2]), [])
        self.assertEqual(plan_question_pages(self._sections(2), []), [[], ])
