"""界面文案底线：不留原样 i18n key、不堆机器语、每个页面有下一步引导。"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

APP = Path("web_v2/app.js")


def _source() -> str:
    return APP.read_text(encoding="utf-8")


def _zh_keys(src: str) -> set[str]:
    zh = src[src.index("const I18N = {"): src.index("    hant: {")]
    return set(re.findall(r'"([a-zA-Z0-9_.]+)":', zh))


MACHINE_TERMS = ("Gate", "schema", "coverage_audit.json", "硬门禁", "机器门禁")


class UiCopyTests(unittest.TestCase):
    def test_every_t_key_exists_in_zh_table(self) -> None:
        src = _source()
        used = set(re.findall(r'(?<![A-Za-z0-9_])t\("([a-zA-Z0-9_.]+)"', src))
        zh = _zh_keys(src)
        missing = sorted(k for k in used if k not in zh)
        self.assertEqual(missing, [], f"这些 key 没进中文文案表，界面会露出机器语：{missing[:10]}")

    def test_no_machine_jargon_in_user_facing_zh_copy(self) -> None:
        src = _source()
        zh = src[src.index("const I18N = {"): src.index("    hant: {")]
        values = "\n".join(re.findall(r'"[a-zA-Z0-9_.]+":\s*"([^"]*)"', zh))
        hits = [term for term in MACHINE_TERMS if term in values]
        self.assertEqual(hits, [], f"中文界面里还有机器语：{hits}")

    def test_guide_page_has_no_placeholder_jargon(self) -> None:
        src = _source()
        values = "\n".join(re.findall(r'"[a-zA-Z0-9_.]+":\s*"([^"]*)"', src))
        self.assertNotIn("guide.json", values, "界面文案不该提文件名")
        self.assertNotIn("待补充（web_v2", values)
        self.assertIn("guide.pendingTitle", src)

    def test_guide_json_has_three_tabs(self) -> None:
        import json
        from pathlib import Path
        guide = Path("web_v2/guide.json").read_text(encoding="utf-8")
        content = json.loads(guide)
        labels = [t.get("label") for t in content.get("tabs", [])]
        self.assertEqual(labels, ["产品介绍", "使用说明", "时间线"])
        for banned in ("第一梯队", "工业级", "100% 完成"):
            self.assertNotIn(banned, guide)
        self.assertIn("DeepSeek", guide)
        self.assertIn("阿里云百炼", guide)
        self.assertIn("Kimi", guide)

    def test_artifact_page_guides_next_step(self) -> None:
        src = _source()
        self.assertIn("artifact.nextStep", src)
        for phrase in ("先通读", "练习", "出卷"):
            self.assertIn(phrase, src)
