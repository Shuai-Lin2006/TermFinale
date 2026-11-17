"""模型 JSON 解析的容错测试：LaTeX 反斜杠不能把整页审计打挂。"""
from __future__ import annotations

import unittest

from tfv2.llm.client import _parse_json, _repair_invalid_escapes


class LLMJsonTests(unittest.TestCase):
    def test_valid_json(self) -> None:
        self.assertEqual(_parse_json('{"a": 1}'), {"a": 1})

    def test_repairs_invalid_latex_escape(self) -> None:
        raw = '{"evidence": "电容 \\mu F 与 \\Omega 的标注"}'
        out = _parse_json(raw)
        self.assertIn("\\mu", out["evidence"])
        self.assertIn("\\Omega", out["evidence"])

    def test_repairs_u_prefixed_latex_commands(self) -> None:
        raw = '{"evidence": "\\underline{a} 与 \\uparrow"}'
        out = _parse_json(raw)
        self.assertIn("\\underline", out["evidence"])
        self.assertIn("\\uparrow", out["evidence"])

    def test_keeps_double_backslash(self) -> None:
        raw = '{"evidence": "公式 \\\\frac{1}{2}"}'
        out = _parse_json(raw)
        self.assertIn("\\frac", out["evidence"])

    def test_repair_does_not_touch_valid_escapes(self) -> None:
        self.assertEqual(_repair_invalid_escapes(r'"a\nb"'), r'"a\nb"')

    def test_extracts_object_from_text(self) -> None:
        self.assertEqual(_parse_json('说明：{"ok": true} 结束'), {"ok": True})


if __name__ == "__main__":
    unittest.main()
