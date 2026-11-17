"""PDF 目录页码回填测试（不跑浏览器）。"""
from __future__ import annotations

import unittest

from tfv2.render.pdf import _set_toc_pages


class PdfTocTests(unittest.TestCase):
    def test_only_matching_anchor_is_updated(self) -> None:
        html = (
            '<a href="#a"><span>A</span><span class="page">3</span></a>'
            '<a href="#b"><span>B</span><span class="page">4</span></a>'
        )
        out = _set_toc_pages(html, {"a": 7})
        self.assertIn('<a href="#a"><span>A</span><span class="page">7</span></a>', out)
        self.assertIn('<a href="#b"><span>B</span><span class="page">4</span></a>', out)


if __name__ == "__main__":
    unittest.main()
