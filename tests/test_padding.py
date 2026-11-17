
"""Anti-padding checks: quotas must not become repeated filler."""
from __future__ import annotations

import unittest

from tfv2.quality import padding


class PaddingTests(unittest.TestCase):
    def test_generic_transition_is_flagged(self) -> None:
        section = {"title": "s", "blocks": [
            {"kind": "paragraph", "text": "本节介绍了内脏神经。"},
        ]}
        self.assertTrue(padding.audit_section(section))

    def test_concrete_content_passes(self) -> None:
        section = {"title": "s", "blocks": [
            {"kind": "paragraph", "text": "内脏感觉神经的阈值较高，正常胃肠蠕动不会引起主观感觉。只有牵拉、痉挛等较强刺激才会产生疼痛。"},
            {"kind": "paragraph", "text": "牵涉性痛是内脏病变在体表特定区域产生的痛觉或感觉过敏，其体表区域相对固定。"},
            {"kind": "example", "text": "例1：牵拉肠系膜引起疼痛。步骤：先确认刺激位于内脏，再观察体表牵涉区域。"},
        ]}
        self.assertEqual(padding.audit_section(section), [])

    def test_duplicate_paragraph_is_flagged(self) -> None:
        text = "内脏感觉神经把刺激传入中枢，阈值较高，正常活动不引起感觉。"
        section = {"title": "s", "blocks": [
            {"kind": "paragraph", "text": text},
            {"kind": "paragraph", "text": text},
        ]}
        self.assertTrue(any("重复" in x for x in padding.audit_section(section)))

    def test_empty_example_is_flagged(self) -> None:
        section = {"title": "s", "blocks": [
            {"kind": "example", "text": "请思考一个例子。"},
        ]}
        self.assertTrue(padding.audit_section(section))


if __name__ == "__main__":
    unittest.main()
