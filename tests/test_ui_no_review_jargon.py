"""发布前文案：界面上不再显示“待复核/未通过/复核范围”这类内部状态词。"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

APP = Path("web_v2/app.js")
BANNED = ("待复核", "待複核", "复核范围", "複核範圍", "未通过", "未透過", "Needs review", "未達可讀")


class NoReviewJargonTests(unittest.TestCase):
    def test_zh_values_have_no_internal_status_words(self) -> None:
        src = APP.read_text(encoding="utf-8")
        zh = src[src.index("const I18N = {"): src.index("    hant: {")]
        values = "\n".join(re.findall(r'"[a-zA-Z0-9_.]+":\s*"([^"]*)"', zh))
        hits = [w for w in BANNED if w in values]
        self.assertEqual(hits, [], f"界面文案里还有内部状态词：{hits}")

    def test_status_labels_are_user_facing(self) -> None:
        src = APP.read_text(encoding="utf-8")
        self.assertIn('"status.review": "已生成"', src)
        self.assertIn('"status.rejected": "需重做"', src)
