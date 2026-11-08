"""证据卡：引文由程序填，模型解释；伪造 eid 不生效。"""
from __future__ import annotations

import json
import unittest

from core.generate.card_guide import generate_card_chapter

RAW = "【《高数》第 1 页】\n隐函数求导：方程两边对 x 求导，再解出 y'。\n这是本章核心。"


def fake_ai(sys_p, user, **kwargs):
    return json.dumps({"cards": [{"eid": "E1", "explain": "把 y 看成 x 的函数，遇到 y 就补 y'。"}]},
                      ensure_ascii=False)


class CardGuideTest(unittest.TestCase):
    def test_render_quotes_from_source(self):
        md = generate_card_chapter(RAW, chapter={"title": "隐函数", "ban_topics": []}, ai_call=fake_ai)
        self.assertIn("> 原文：", md)
        self.assertIn("（P.1）", md)
        self.assertIn("把 y 看成 x 的函数", md)

    def test_fake_quote_cannot_appear(self):
        md = generate_card_chapter(RAW, chapter={"title": "隐函数"}, ai_call=fake_ai)
        self.assertNotIn("编造的原文", md)

    def test_material_prefix_page_number(self):
        raw = ("【重点资料·权重3：高数.pdf】\n【《高数.pdf》第 2 页】\n"
               "参数方程求导：dy/dx=(dy/dt)/(dx/dt)。这是第二页内容。")
        md = generate_card_chapter(raw, chapter={"title": "参数"}, ai_call=fake_ai)
        self.assertIn("（P.2）", md)
        self.assertNotIn("（P.1）", md)

    def test_fallback_image_page(self):
        raw = "【《高数》第 3 页】\n[[[IMAGE: f.png | 图注: 电路图（第 3 页）]]]"
        md = generate_card_chapter(raw, chapter={"title": "图"}, ai_call=fake_ai)
        self.assertIn("（P.3）", md)
        self.assertIn("图示", md)

    def test_fallback_skips_prompt_wrapper(self):
        raw = "【本章资料】\n【《高数》第 9 页】\n这是第九页真正的正文内容，足够长。"
        md = generate_card_chapter(raw, chapter={"title": "测试"}, ai_call=fake_ai)
        self.assertNotIn("【本章资料】", md)

    def test_fallback_filtered_by_ban(self):
        raw = "【《高数》第 1 页】\n参数方程求导的完整步骤和说明。"
        md = generate_card_chapter(raw, chapter={"title": "x", "ban_topics": ["参数方程"]}, ai_call=fake_ai)
        self.assertNotIn("参数方程", md)

    def test_broken_math_card_dropped(self):
        raw = "【《高数》第 1 页】\n\\begin{aligned} x+1"
        md = generate_card_chapter(raw, chapter={"title": "x"}, ai_call=fake_ai)
        self.assertNotIn("\\begin", md)

    def test_blank_page_creates_placeholder(self):
        raw = "【《高数》第 5 页】\n"
        md = generate_card_chapter(raw, chapter={"title": "空页"}, ai_call=fake_ai)
        self.assertIn("（P.5）", md)
        self.assertIn("保留原页", md)

    def test_explain_strips_source_page_ref(self):
        from core.generate.card_guide import _clean_explain
        self.assertNotIn("第104页", _clean_explain("见第104页", []))
