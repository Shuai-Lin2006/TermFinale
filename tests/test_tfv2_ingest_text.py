"""资料文本清洗测试。"""
from __future__ import annotations

import unittest

from tfv2.ingest.text import sanitize_text


class TextSanitizeTests(unittest.TestCase):
    def test_symbol_private_use_maps_to_omega(self) -> None:
        self.assertEqual(sanitize_text("2\uf057"), "2Ω")

    def test_control_chars_removed(self) -> None:
        self.assertEqual(sanitize_text("a\x00\x07b"), "ab")

    def test_replacement_char_removed(self) -> None:
        self.assertEqual(sanitize_text("a\ufffdb"), "ab")


if __name__ == "__main__":
    unittest.main()
