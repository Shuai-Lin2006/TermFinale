"""图文配对：缺文件/图注/页不符必须报错。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from core.quality.image_pairing import audit_images


class ImagePairTest(unittest.TestCase):
    def test_valid_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            Image.new("RGB", (320, 240), "white").save(Path(d) / "fig1.png")
            src = ["【《x》第 1 页】\n[[[IMAGE: fig1.png | 图注: 隐函数切线（第 1 页）]]]"]
            md = ("[[[IMAGE: fig1.png | 图注: 隐函数切线（第 1 页）]]]\n"
                  "[[[IMAGE: fig2.png | 图注: 缺图（第 1 页）]]]")
            r = audit_images(md, src, d)
            self.assertEqual(r.total, 2)
            self.assertEqual(r.paired, 1)
            self.assertTrue(any("不存在" in i.reason for i in r.issues))
