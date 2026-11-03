"""流水线测试：导出、解析、验卷（全部离线，不调用 AI）。"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("TERMFINALE_HOME", tempfile.mkdtemp(prefix="tf_pipe_"))
os.environ.setdefault("TERMFINALE_DISABLE_VISION", "1")

from core import paths  # noqa: E402
from core.exporter import export_to_html  # noqa: E402
from core.parser import extract_text_from_file  # noqa: E402
from core.generate.exam_builder import build_blueprint, validate_paper  # noqa: E402


def _export(markdown: str, name: str = "out.html") -> str:
    paths.ensure_dirs()
    target = paths.debug_dir() / name
    export_to_html(markdown, str(target), lang="中文")
    return target.read_text(encoding="utf-8")


class ExporterTest(unittest.TestCase):
    def test_chapter_numbering_skips_continuation(self):
        md = ("## 核心考点：甲\n\n正文一\n\n"
              "## 核心考点：乙（续）\n\n续写内容\n\n"
              "## 核心考点：丙\n\n正文二")
        html = _export(md, "chapters.html")
        titles = [re.sub(r"<[^>]+>", "", h) for h in
                  re.findall(r'class="chapter-title"[^>]*>(.*?)</h2>', html)]
        self.assertEqual(titles, ["第 1 章：甲", "第 2 章：丙"])

    def test_blank_space(self):
        html = _export("1. 题目一\n\n[[BLANK:120]]\n\n2. 题目二", "blank.html")
        self.assertIn('class="blank-space"', html)
        self.assertIn("height:120px", html)

    def test_keyword_and_math(self):
        html = _export("## 核心考点：测试\n\n公式 $a^2+b^2=c^2$，名词 [[力|相互作用]]", "kw.html")
        self.assertIn('class="keyword"', html)
        self.assertIn("a^2+b^2=c^2", html)

    def test_inline_image(self):
        from PIL import Image

        paths.ensure_dirs()
        Image.new("RGB", (60, 40), "white").save(paths.assets_dir() / "unit.png")
        html = _export("正文\n\n[[[IMAGE: unit.png | 图注: 单元测试图]]]", "img.html")
        self.assertIn("data:image/png;base64,", html)
        self.assertIn("单元测试图", html)
        self.assertNotIn("[[[IMAGE:", html)

    def test_empty_markdown(self):
        html = _export("", "empty.html")
        self.assertIn("<html", html)


class ParserTest(unittest.TestCase):
    def test_docx(self):
        from docx import Document

        doc = Document()
        doc.add_paragraph("理想气体状态方程 pV=nRT")
        path = Path(tempfile.mkdtemp()) / "t.docx"
        doc.save(path)
        pages = extract_text_from_file(str(path))
        self.assertTrue(pages)
        self.assertIn("pV=nRT", "\n".join(pages))

    def test_pptx(self):
        from pptx import Presentation

        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = "测试幻灯片标题"
        path = Path(tempfile.mkdtemp()) / "t.pptx"
        prs.save(path)
        pages = extract_text_from_file(str(path))
        self.assertTrue(pages)
        self.assertIn("测试幻灯片标题", "\n".join(pages))


class ExamTest(unittest.TestCase):
    def _paper(self) -> str:
        q = lambda i: (f"{i}. 关于刚体转动的说法，下列正确的是（ ）\n"
                       "A. 与质量无关\nB. 与转轴位置有关\nC. 与角速度无关\nD. 以上都不对\n【考点：转动惯量】\n")
        selection = "\n".join(q(i) for i in range(1, 11))
        fill = "\n".join(f"{i}. 转动惯量定义式 ____。【考点：转动惯量】\n" for i in range(1, 6))
        calc = "\n".join(f"{i}. 求转动惯量 $J=\\frac{{1}}{{2}}mR^2$【考点：转动惯量】\n\n" for i in range(1, 4))
        comp = "1. 细棒下摆求角速度 $\\omega=\\sqrt{3g/L}$【考点：机械能守恒】\n"
        return (f"# 试卷\n## 一、选择题（每题3分，共30分）\n{selection}\n"
                f"## 二、填空题（每题4分，共20分）\n{fill}\n"
                f"## 三、计算题（每题10分，共30分）\n{calc}\n"
                f"## 四、综合题（每题20分，共20分）\n{comp}\n# 答案与解析\n1. B\n")

    def test_complete_paper_passes(self):
        report = validate_paper(self._paper(), build_blueprint(3, 80))
        self.assertTrue(report.ok, report.issues)
        self.assertEqual(report.metrics["score_total"], 100.0)

    def test_missing_section_fails(self):
        broken = self._paper().split("## 三、计算题")[0]
        report = validate_paper(broken, build_blueprint(3, 80))
        self.assertFalse(report.ok)
        self.assertTrue(any("缺少大题" in i for i in report.issues))


if __name__ == "__main__":
    unittest.main(verbosity=2)
