"""v2 原生 Word (.docx) 渲染测试。"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image

from tests.test_tfv2_lecture import make_spec, src
from tfv2.domain.lecture import BlockKind, FigureRef, LectureBlock
from tfv2.render.docx import _latex_to_text, write_docx


def _spec_with_blocks(*, asset_path: str = "fig.png"):
    spec = make_spec()
    section = spec.sections[0]
    section.blocks = [
        LectureBlock(
            id="p1",
            kind=BlockKind.PARAGRAPH,
            text="导数的定义与几何意义。",
            source_refs=[src(1)],
        ),
        LectureBlock(
            id="f1",
            kind=BlockKind.FORMULA,
            text=r"$\frac{\tau^2}{2} \le \mu \cdot \Omega$",
            source_refs=[src(1)],
        ),
        LectureBlock(
            id="ex1",
            kind=BlockKind.EXAMPLE,
            text="例1：先求导，再代入。",
            source_refs=[src(1)],
        ),
        LectureBlock(id="pt1", kind=BlockKind.PITFALL, text="易错点：不要漏掉链式法则。"),
        LectureBlock(id="sm1", kind=BlockKind.SUMMARY, text="小结：导数是切线斜率。"),
        LectureBlock(
            id="fig1",
            kind=BlockKind.FIGURE,
            text="",
            source_refs=[src(2)],
            figure=FigureRef(
                image_id="img1",
                caption="图 1 导数的几何意义",
                source=src(2),
                after_block_id="fig1",
                asset_path=asset_path,
            ),
        ),
    ]
    section.source_refs = [src(1), src(2)]
    return spec


def _tiny_png(path: Path) -> None:
    Image.new("RGB", (120, 80), "white").save(path)


def _has_typst() -> bool:
    return bool(shutil.which("typst")) or Path("tools/typst").is_file() or Path("tools/typst.exe").is_file()


@unittest.skipUnless(_has_typst(), "需要 Typst 才能渲染公式图片")
class DocxRenderTests(unittest.TestCase):
    def test_renders_native_textbook_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work = Path(temp_dir)
            _tiny_png(work / "fig.png")
            spec = _spec_with_blocks()

            out = write_docx(spec, work / "讲义.docx", base_dir=work)

            self.assertTrue(out.is_file())
            self.assertEqual(out.suffix, ".docx")
            document = Document(str(out))
            paragraphs = document.paragraphs
            texts = [paragraph.text for paragraph in paragraphs]
            joined = "\n".join(texts)

            # 标头 / 标题 / 小标题
            title = next(p for p in paragraphs if p.style.name == "Title" and p.text == "高等数学")
            self.assertIsNotNone(title)
            self.assertIn("TermFinale精品讲义", joined)
            self.assertIn("高数讲义", joined)
            section_heading = next(
                p for p in paragraphs if p.style.name == "Heading 1" and p.text == "第一节 导数"
            )
            self.assertIsNotNone(section_heading)

            # 目录
            self.assertIn("目录", texts)
            self.assertTrue(any(text.startswith("第一节 导数\t1") for text in texts))

            # 摘要、正文、例题/易错/小结、结语
            for expected in (
                "这份资料讲导数与微分。",
                "导数",
                "微分",
                "导数的定义与几何意义。",
                "例题：",
                "先求导，再代入。",
                "易错：",
                "小结：",
                "结语",
                "把这一章啃下来。",
            ):
                self.assertIn(expected, joined)
            self.assertNotIn("例1", joined)

            # 顺序：标头 -> 目录 -> 摘要 -> 正文 -> 结语
            title_index = texts.index("高数讲义")
            toc_index = texts.index("目录")
            summary_index = texts.index("本资料讲什么")
            section_index = next(i for i, p in enumerate(paragraphs) if p is section_heading)
            closing_index = texts.index("结语")
            self.assertLess(title_index, toc_index)
            self.assertLess(summary_index, toc_index)
            self.assertLess(summary_index, section_index)
            self.assertLess(section_index, closing_index)

            # 公式：优先渲染为图片；任何情况下都不能留下原始 LaTeX
            self.assertGreaterEqual(len(document.inline_shapes), 1)
            for paragraph_text in texts:
                self.assertNotIn("\\frac", paragraph_text)
                self.assertNotIn("\\tau", paragraph_text)
                self.assertNotIn("$", paragraph_text)

            # 图片、图注、图片出处、小节出处
            self.assertGreaterEqual(len(document.inline_shapes), 1)
            self.assertIn("图 1 导数的几何意义", joined)
            self.assertIn("出处：第 2 页", joined)
            self.assertIn("出处：第 1–2 页", joined)

            # 标头不出现源文件名；人设不进入成稿
            self.assertNotIn("高数.pdf", joined)
            self.assertNotIn("老师", joined)

            # 页脚：生成信息 + PAGE 域
            footer = document.sections[0].footer
            footer_text = "\n".join(p.text for p in footer.paragraphs)
            self.assertIn("TermFinale", footer_text)
            self.assertIn("高数.pdf", footer_text)
            self.assertIn("100", footer_text)
            self.assertIn("具体请以实际资料为准", footer_text)
            self.assertIn("第", footer_text)
            self.assertIn("页", footer_text)
            footer_xml = "".join(p._p.xml for p in footer.paragraphs)
            self.assertIn("PAGE", footer_xml)
            self.assertIn("NUMPAGES", footer_xml)

            # 原生 Word，不夹带阅读器 HTML/JS
            self.assertNotIn("tfReaderTools", document.element.xml)
            self.assertNotIn("<script", document.element.xml)

    def test_table_formula_figure_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work = Path(temp_dir)
            _tiny_png(work / "fig.png")
            spec = _spec_with_blocks()
            spec.sections[0].blocks.insert(0, LectureBlock(
                id="t1", kind=BlockKind.PARAGRAPH,
                text="| 名称 | 值 |\n| --- | --- |\n| a | 1 |\n| b | 2 |",
                source_refs=[src(1)],
            ))
            out = write_docx(spec, work / "all.docx", base_dir=work)
            document = Document(str(out))
            self.assertEqual(len(document.tables), 1)
            table = document.tables[0]
            self.assertIsNotNone(table.rows[0]._tr.find(qn("w:trPr")).find(qn("w:tblHeader")))
            self.assertGreaterEqual(len(document.inline_shapes), 2)
            for shape in document.inline_shapes:
                self.assertLessEqual(shape.height.cm, 6.5)
                self.assertLessEqual(shape.width.cm, 9.6)
            joined = "\n".join(p.text for p in document.paragraphs)
            self.assertNotIn("$", joined)
            self.assertNotIn("\\frac", joined)

    def test_inline_formula_is_rendered_as_image(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work = Path(temp_dir)
            spec = _spec_with_blocks()
            spec.sections[0].blocks.insert(0, LectureBlock(
                id="p0", kind=BlockKind.PARAGRAPH,
                text=r"圆的方程是 $x^2+y^2=r^2$。",
                source_refs=[src(1)],
            ))
            out = write_docx(spec, work / "inline.docx", base_dir=work)
            document = Document(str(out))
            joined = "\n".join(p.text for p in document.paragraphs)
            self.assertNotIn("$x^2", joined)
            self.assertNotIn("\\frac", joined)
            self.assertGreaterEqual(len(document.inline_shapes), 2)

    def test_missing_image_is_explicit_and_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work = Path(temp_dir)
            spec = _spec_with_blocks(asset_path="does-not-exist.png")

            out = write_docx(spec, work / "missing.docx", base_dir=work)

            document = Document(str(out))
            joined = "\n".join(p.text for p in document.paragraphs)
            self.assertIn("图片缺失", joined)
            self.assertIn("图 1 导数的几何意义", joined)
            self.assertIn("出处：第 2 页", joined)
            # One formula image is expected; the missing figure must not add another.
            self.assertGreaterEqual(len(document.inline_shapes), 1)

    def test_corrupt_image_is_explicit_and_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work = Path(temp_dir)
            (work / "fig.png").write_bytes(b"not really a png")
            spec = _spec_with_blocks()

            out = write_docx(spec, work / "corrupt.docx", base_dir=work)

            document = Document(str(out))
            joined = "\n".join(p.text for p in document.paragraphs)
            self.assertIn("图片缺失", joined)
            self.assertGreaterEqual(len(document.inline_shapes), 1)


class LatexFallbackTests(unittest.TestCase):
    def test_common_latex_becomes_readable_text(self) -> None:
        text = _latex_to_text(
            r"$\frac{a+b}{2} \le \tau \cdot \mu \Omega \infty \pi \neq \times \, "
            r"\text{当 } x_{n}^{2} \to \sqrt{y}$"
        )
        self.assertIn("(a+b)/(2)", text)
        self.assertIn("≤", text)
        self.assertIn("τ", text)
        self.assertIn("·", text)
        self.assertIn("μ", text)
        self.assertIn("Ω", text)
        self.assertIn("∞", text)
        self.assertIn("π", text)
        self.assertIn("≠", text)
        self.assertIn("×", text)
        self.assertIn("当", text)
        self.assertIn("x_n^2", text)
        self.assertIn("→", text)
        self.assertIn("√(y)", text)
        self.assertNotIn("\\", text)
        self.assertNotIn("$", text)

    def test_nested_fraction_and_unknown_command(self) -> None:
        text = _latex_to_text(r"\frac{\frac{1}{2}}{3} + \unknowncmd{x}")
        self.assertIn("((1)/(2))/(3)", text)
        self.assertNotIn("\\", text)
        self.assertIn("x", text)


if __name__ == "__main__":
    unittest.main()
