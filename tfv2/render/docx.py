"""LectureSpec -> 原生 Word (.docx)。

排版原则与阅读器 HTML 版一致：标头、目录、摘要、正文、图注/出处、结语、
页脚小字。公式不依赖 KaTeX，直接降级为可读的 Unicode/线性文本。

只依赖 python-docx（Pillow 仅用于按原始像素尺寸限制图片宽度）。
"""
from __future__ import annotations

import re
import shutil
import sys
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from tfv2.render.formula_image import formula_png

from tfv2.domain.lecture import (
    BlockKind,
    LectureBlock,
    LectureSection,
    LectureSpec,
    SourceRef,
)

MAX_FIGURE_WIDTH_CM = 9.5
MAX_FIGURE_HEIGHT_CM = 6.5
MISSING_IMAGE_TEXT = "图片缺失（需重新抽取）"
_PIPE_TABLE = re.compile(r"(?:^\|.+\|\s*$[\n\r]*)+", flags=re.M)


def _add_md_table(doc, md: str) -> None:
    """Render a Markdown pipe table as a real Word table."""
    rows = [line for line in md.strip().splitlines() if line.strip()]
    if len(rows) < 2:
        _add_text_paragraph(doc, md.strip())
        return
    def cells(line: str):
        return [c.strip() for c in line.strip().strip("|").split("|")]
    header = cells(rows[0])
    body_rows = []
    for row in rows[1:]:
        if all(re.fullmatch(r":?-{1,}:?", c) for c in cells(row)):
            continue
        body_rows.append(cells(row))
    if not body_rows:
        _add_text_paragraph(doc, md.strip())
        return
    table = doc.add_table(rows=1 + len(body_rows), cols=len(header))
    table.style = "Table Grid"
    # Repeat the header on every page and keep each row in one piece.
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    header_flag = OxmlElement("w:tblHeader")
    header_flag.set(qn("w:val"), "true")
    tr_pr.append(header_flag)
    for row in table.rows:
        row_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        row_pr.append(cant_split)
    for j, cell_text in enumerate(header):
        cell = table.cell(0, j)
        cell.text = ""
        run = cell.paragraphs[0].add_run(_plain(cell_text))
        run.bold = True
    for i, row in enumerate(body_rows, start=1):
        for j in range(len(header)):
            cell = table.cell(i, j)
            cell.text = ""
            cell.paragraphs[0].add_run(_plain(row[j] if j < len(row) else ""))
    doc.add_paragraph()

_INK = RGBColor(0x1F, 0x23, 0x28)
_MUTED = RGBColor(0x5B, 0x64, 0x70)
_BRAND = RGBColor(0x24, 0x5C, 0x73)

# LaTeX 命令 -> 可读字符。未列出的命令会被丢弃，保证输出里没有反斜杠命令。
_LATEX_SYMBOLS: dict[str, str] = {
    # 希腊字母
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "varepsilon": "ε",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "vartheta": "ϑ",
    "iota": "ι",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "pi": "π",
    "Pi": "Π",
    "rho": "ρ",
    "sigma": "σ",
    "Sigma": "Σ",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "varphi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
    "Omega": "Ω",
    "Gamma": "Γ",
    "Delta": "Δ",
    "Theta": "Θ",
    "Lambda": "Λ",
    "Xi": "Ξ",
    "Phi": "Φ",
    "Psi": "Ψ",
    # 关系/运算
    "le": "≤",
    "leq": "≤",
    "ge": "≥",
    "geq": "≥",
    "neq": "≠",
    "ne": "≠",
    "approx": "≈",
    "equiv": "≡",
    "sim": "∼",
    "propto": "∝",
    "times": "×",
    "cdot": "·",
    "div": "÷",
    "pm": "±",
    "mp": "∓",
    "infty": "∞",
    "partial": "∂",
    "nabla": "∇",
    "sum": "∑",
    "prod": "∏",
    "int": "∫",
    "oint": "∮",
    "to": "→",
    "rightarrow": "→",
    "leftarrow": "←",
    "Rightarrow": "⇒",
    "Leftarrow": "⇐",
    "Leftrightarrow": "⇔",
    "in": "∈",
    "notin": "∉",
    "subset": "⊂",
    "subseteq": "⊆",
    "supset": "⊃",
    "supseteq": "⊇",
    "cup": "∪",
    "cap": "∩",
    "emptyset": "∅",
    "forall": "∀",
    "exists": "∃",
    "therefore": "∴",
    "because": "∵",
    "ldots": "…",
    "dots": "…",
    "cdots": "⋯",
    "vdots": "⋮",
    "angle": "∠",
    "perp": "⊥",
    "parallel": "∥",
    "degree": "°",
    "circ": "∘",
    "prime": "′",
    "quad": " ",
    "qquad": "  ",
    # 函数名
    "sin": "sin",
    "cos": "cos",
    "tan": "tan",
    "cot": "cot",
    "sec": "sec",
    "csc": "csc",
    "arcsin": "arcsin",
    "arccos": "arccos",
    "arctan": "arctan",
    "sinh": "sinh",
    "cosh": "cosh",
    "tanh": "tanh",
    "log": "log",
    "ln": "ln",
    "lg": "lg",
    "exp": "exp",
    "lim": "lim",
    "max": "max",
    "min": "min",
    "sup": "sup",
    "inf": "inf",
    "det": "det",
    "gcd": "gcd",
}

_IGNORED_COMMANDS = {
    "left",
    "right",
    "big",
    "Big",
    "bigg",
    "Bigg",
    "bigl",
    "bigr",
    "Bigl",
    "Bigr",
    "displaystyle",
    "textstyle",
    "scriptstyle",
    "limits",
    "nolimits",
    "mathrm",
    "mathbf",
    "mathit",
    "mathsf",
    "operatorname",
    "mbox",
    "begin",
    "end",
}


def _read_group(text: str, start: int) -> tuple[str | None, int]:
    """读取以 ``{`` 开头的平衡花括号组，返回 (内容, 结束位置)。"""
    if start >= len(text) or text[start] != "{":
        return None, start
    depth = 0
    for pos in range(start, len(text)):
        char = text[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : pos], pos + 1
    return text[start + 1 :], len(text)


def _latex_to_text(latex: str) -> str:
    """把常见 LaTeX 片段降级为可读的 Unicode/线性文本。

    不含任何 HTML/KaTeX 依赖；返回值里不会留下反斜杠命令或 ``$``。
    """
    text = (latex or "").replace("$$", "").replace("$", "")
    text = (
        text.replace("\\[", "")
        .replace("\\]", "")
        .replace("\\(", "")
        .replace("\\)", "")
    )

    def convert(source: str) -> str:
        out: list[str] = []
        pos = 0
        while pos < len(source):
            char = source[pos]
            if char == "\\":
                if pos + 1 >= len(source):
                    pos += 1
                    continue
                nxt = source[pos + 1]
                if nxt == "\\":
                    out.append("\n")
                    pos += 2
                    continue
                if not nxt.isalpha():
                    # \,, \!, \;, \:, \%, \{, \}, \_, \& ...
                    if nxt in ",!;:":
                        pos += 2
                        continue
                    escaped = {"%": "%", "{": "{", "}": "}", "_": "_", "&": "&", "#": "#", " ": " "}
                    out.append(escaped.get(nxt, nxt))
                    pos += 2
                    continue
                end = pos + 1
                while end < len(source) and source[end].isalpha():
                    end += 1
                command = source[pos + 1 : end]
                if command == "frac":
                    numerator, after_num = _read_group(source, end)
                    denominator, after_den = _read_group(source, after_num)
                    if numerator is not None and denominator is not None:
                        out.append(f"({convert(numerator)})/({convert(denominator)})")
                        pos = after_den
                    else:
                        out.append("/")
                        pos = end
                    continue
                if command in ("text", "mathrm", "mathbf", "mathit", "mathsf", "operatorname", "mbox"):
                    body, after = _read_group(source, end)
                    if body is not None:
                        out.append(convert(body))
                        pos = after
                    else:
                        pos = end
                    continue
                if command == "sqrt":
                    cursor = end
                    index = ""
                    if cursor < len(source) and source[cursor] == "[":
                        close = source.find("]", cursor)
                        if close != -1:
                            index = convert(source[cursor + 1 : close])
                            cursor = close + 1
                    body, after = _read_group(source, cursor)
                    if body is not None:
                        root = "√" + (f"[{index}]" if index else "") + f"({convert(body)})"
                        out.append(root)
                        pos = after
                    else:
                        out.append("√")
                        pos = cursor
                    continue
                if command in _IGNORED_COMMANDS:
                    pos = end
                    continue
                mapped = _LATEX_SYMBOLS.get(command)
                if mapped is not None:
                    out.append(mapped)
                # 未识别的命令直接丢弃，避免把 \command 留在正文里。
                pos = end
                continue
            if char in "_^":
                out.append(char)
                nxt = pos + 1
                if nxt < len(source) and source[nxt] == "{":
                    body, after = _read_group(source, nxt)
                    out.append(convert(body or ""))
                    pos = after
                else:
                    if nxt < len(source):
                        out.append(source[nxt])
                        nxt += 1
                    pos = nxt
                continue
            if char in "{}":
                pos += 1
                continue
            out.append(char)
            pos += 1
        return "".join(out)

    result = convert(text)
    result = result.replace("\r\n", "\n").replace("\r", "\n")
    result = re.sub(r"[ \t]{2,}", " ", result)
    result = "\n".join(line.strip() for line in result.split("\n"))
    return result.strip()


def _plain(text: str | None) -> str:
    """普通文本里若混入 LaTeX/公式定界符，也一并降级。"""
    value = text or ""
    if "\\" in value or "$" in value:
        return _latex_to_text(value)
    return value


def _pages_label(refs: list[SourceRef]) -> str:
    pages: list[int] = []
    for ref in refs:
        start = ref.page_start
        end = ref.page_end or start
        pages.extend(range(start, end + 1))
    pages = sorted(set(pages))
    if not pages:
        return ""
    ranges: list[str] = []
    index = 0
    while index < len(pages):
        end = index
        while end + 1 < len(pages) and pages[end + 1] == pages[end] + 1:
            end += 1
        ranges.append(f"{pages[index]}" if index == end else f"{pages[index]}–{pages[end]}")
        index = end + 1
    return "第 " + "、".join(ranges) + " 页"


def _set_east_asia(style, font_name: str) -> None:
    try:
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.get_or_add_rFonts()
        rfonts.set(qn("w:eastAsia"), font_name)
    except (AttributeError, KeyError, ValueError):
        pass


def _configure_document(doc, spec: LectureSpec) -> None:
    normal = doc.styles["Normal"]
    # 同时设置 ascii/hAnsi 与 eastAsia：只设 eastAsia 时 LibreOffice 仍会用 Calibri 渲染中文，出现方框。
    normal.font.name = "Arial Unicode MS"
    normal.font.size = Pt(11)
    normal.font.color.rgb = _INK
    _set_east_asia(normal, "Arial Unicode MS")

    for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        try:
            style = doc.styles[name]
        except KeyError:
            continue
        style.font.name = "Arial Unicode MS"
        style.font.color.rgb = _INK
        _set_east_asia(style, "Arial Unicode MS")

    try:
        footer_style = doc.styles["Footer"]
        footer_style.font.size = Pt(8)
        footer_style.font.color.rgb = _MUTED
        _set_east_asia(footer_style, "Arial Unicode MS")
    except KeyError:
        pass

    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

    doc.core_properties.title = spec.header.title
    doc.core_properties.subject = spec.header.course
    doc.core_properties.author = spec.footer.agent_name


def _add_text_paragraph(
    doc,
    text: str,
    *,
    style: str | None = None,
    bold_label: str | None = None,
    italic: bool = False,
):
    paragraph = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    if bold_label:
        label_run = paragraph.add_run(bold_label)
        label_run.bold = True
    lines = (text or "").split("\n")
    for index, line in enumerate(lines):
        if index:
            paragraph.add_run().add_break()
        _add_inline_formulas(paragraph, line, italic=italic)
    return paragraph


_INLINE_FORMULA = re.compile(r"(\$\$.+?\$\$|\$.+?\$)")


def _add_inline_formulas(paragraph, text: str, *, italic: bool = False) -> None:
    """Render inline $...$ as images; never leave raw LaTeX in Word."""
    pos = 0
    for match in _INLINE_FORMULA.finditer(text or ""):
        if match.start() > pos:
            run = paragraph.add_run(_plain(text[pos: match.start()]))
            run.italic = italic
        formula = match.group(0)
        png = formula_png(formula)
        if png:
            try:
                paragraph.add_run().add_picture(BytesIO(png), width=Cm(4.0))
            except Exception:
                paragraph.add_run(_latex_to_text(formula))
        else:
            paragraph.add_run(_latex_to_text(formula))
        pos = match.end()
    if pos < len(text or ""):
        run = paragraph.add_run(_plain(text[pos:]))
        run.italic = italic


def _add_header(doc, spec: LectureSpec) -> None:
    header = spec.header
    kind = "试卷" if any(k in header.title for k in ("试卷", "出卷", "真题")) else ("提取" if any(k in header.title for k in ("提取", "考点", "名词", "术语", "原题", "逻辑")) else "讲义")
    kicker = doc.add_paragraph()
    kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    kicker_run = kicker.add_run("TermFinale精品" + kind)
    kicker_run.font.size = Pt(9)
    kicker_run.font.color.rgb = _MUTED

    title = doc.add_heading(_plain(header.course), level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run(_plain(header.title))
    subtitle_run.font.size = Pt(11)
    subtitle_run.font.color.rgb = _MUTED

    if header.section_label:
        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle_run = subtitle.add_run(_plain(header.section_label))
        subtitle_run.font.size = Pt(10.5)
        subtitle_run.font.color.rgb = _MUTED

    meta: list[str] = []
    if header.target_score is not None:
        meta.append(f"目标 {header.target_score} 分")
    if header.days_left is not None:
        meta.append(f"剩余 {header.days_left} 天")
    if header.foundation:
        meta.append(f"基础：{header.foundation}")
    if header.coverage_scope:
        meta.append(header.coverage_scope)
    if header.generated_at:
        meta.append(header.generated_at)
    if meta:
        meta_paragraph = doc.add_paragraph()
        meta_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        meta_run = meta_paragraph.add_run(" ｜ ".join(_plain(item) for item in meta))
        meta_run.font.size = Pt(9)
        meta_run.font.color.rgb = _MUTED


def _add_toc(doc, spec: LectureSpec) -> None:
    if not spec.toc:
        return
    doc.add_heading("目录", level=1)
    for item in spec.toc:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Cm(0.6 * (item.level - 1))
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.tab_stops.add_tab_stop(
            Cm(MAX_FIGURE_WIDTH_CM),
            WD_TAB_ALIGNMENT.RIGHT,
            WD_TAB_LEADER.DOTS,
        )
        paragraph.add_run(_plain(item.title))
        paragraph.add_run("\t")
        page_run = paragraph.add_run(str(item.page_no))
        page_run.font.size = Pt(9)
        page_run.font.color.rgb = _MUTED


def _add_bullets(doc, items: list[str]) -> None:
    for item in items:
        try:
            paragraph = doc.add_paragraph(style="List Bullet")
        except KeyError:
            paragraph = doc.add_paragraph()
        paragraph.add_run(_plain(item))


def _add_summary(doc, spec: LectureSpec) -> None:
    summary = spec.summary
    doc.add_heading("本资料讲什么", level=1)
    _add_text_paragraph(doc, summary.overview)
    if summary.knowledge_map:
        doc.add_heading("知识地图", level=2)
        _add_bullets(doc, summary.knowledge_map)
    if summary.exam_focus:
        doc.add_heading("考点分布", level=2)
        _add_bullets(doc, summary.exam_focus)
    if summary.how_to_use:
        _add_text_paragraph(doc, summary.how_to_use, italic=True)


def _add_source_line(doc, refs: list[SourceRef]) -> None:
    label = _pages_label(refs)
    if not label:
        return
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(10)
    run = paragraph.add_run(f"出处：{label}")
    run.font.size = Pt(9)
    run.font.color.rgb = _MUTED


def _resolve_asset(asset_path: str | None, base_dir: Path) -> Path | None:
    if not asset_path:
        return None
    raw = Path(asset_path).expanduser()
    candidate = raw if raw.is_absolute() else base_dir / raw
    if candidate.is_file():
        return candidate
    if raw.is_file():
        return raw
    return None


def _figure_width(path: Path) -> Cm:
    """按图片原始像素/DPI 计算显示宽度，最大 16cm。"""
    try:
        from PIL import Image

        with Image.open(path) as image:
            width_px = image.size[0]
            dpi = image.info.get("dpi")
        x_dpi = float(dpi[0]) if dpi and dpi[0] else 96.0
        native_cm = width_px / max(x_dpi, 1.0) * 2.54
        if native_cm <= 0:
            native_cm = MAX_FIGURE_WIDTH_CM
        return Cm(min(MAX_FIGURE_WIDTH_CM, native_cm))
    except Exception:
        return Cm(MAX_FIGURE_WIDTH_CM)


def _add_figure(doc, block: LectureBlock, base_dir: Path) -> None:
    figure = block.figure
    if figure is None:
        _add_text_paragraph(doc, MISSING_IMAGE_TEXT)
        return

    asset = _resolve_asset(figure.asset_path, base_dir)
    if asset is None:
        missing = doc.add_paragraph()
        missing_run = missing.add_run(MISSING_IMAGE_TEXT)
        missing_run.bold = True
        missing_run.font.color.rgb = RGBColor(0xB4, 0x53, 0x09)
    else:
        picture_paragraph = doc.add_paragraph()
        picture_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        picture_paragraph.paragraph_format.keep_with_next = True
        try:
            width = _figure_width(asset)
            if figure.origin == "schematic":
                width = Cm(9.0)
            height = None
            try:
                from PIL import Image
                with Image.open(asset) as im:
                    w, h = im.size
                if w and h:
                    height_cm = width.cm * h / w
                    if height_cm > MAX_FIGURE_HEIGHT_CM:
                        height = Cm(MAX_FIGURE_HEIGHT_CM)
                        width = Cm(MAX_FIGURE_HEIGHT_CM * w / h)
            except Exception:
                height = None
            if height is None:
                picture_paragraph.add_run().add_picture(str(asset), width=width)
            else:
                picture_paragraph.add_run().add_picture(str(asset), width=width, height=height)
        except Exception:
            # 扩展名像图片但内容损坏时，清掉空段落，换成明确的缺失提示。
            picture_paragraph._element.getparent().remove(picture_paragraph._element)
            _add_text_paragraph(doc, MISSING_IMAGE_TEXT)

    caption = doc.add_paragraph()
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_after = Pt(2)
    caption.paragraph_format.keep_with_next = True
    caption_run = caption.add_run(_plain(figure.caption))
    caption_run.italic = True
    caption_run.font.size = Pt(9)
    caption_run.font.color.rgb = _MUTED

    label = _pages_label([figure.source])
    if label:
        source = doc.add_paragraph()
        source.alignment = WD_ALIGN_PARAGRAPH.CENTER
        source.paragraph_format.space_after = Pt(12)
        source_run = source.add_run(f"出处：{label}")
        source_run.font.size = Pt(9)
        source_run.font.color.rgb = _MUTED


def _strip_example_number(text: str) -> str:
    stripped = re.sub(r"^\s*例\s*\d+\s*[：:]\s*", "", text or "")
    return re.sub(r"^\s*(例题|例)\s*[：:]\s*", "", stripped)


def _strip_label(text: str, pattern: str) -> str:
    return re.sub(rf"^\s*(?:{pattern})\s*[：:]\s*", "", text or "")


def _add_block(doc, block: LectureBlock, base_dir: Path) -> None:
    kind = block.kind
    if kind == BlockKind.FIGURE:
        _add_figure(doc, block, base_dir)
        return
    if kind == BlockKind.FORMULA:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(6)
        paragraph.paragraph_format.space_after = Pt(10)
        png = formula_png(block.text)
        if png:
            paragraph.add_run().add_picture(BytesIO(png), width=Cm(9.0))
        else:
            # Last resort is readable linear text; never raw backslash commands.
            paragraph.add_run(_latex_to_text(block.text))
        return
    if kind == BlockKind.EXAMPLE:
        _add_text_paragraph(
            doc,
            _strip_example_number(block.text),
            bold_label="例题：",
        )
        return
    if kind == BlockKind.PITFALL:
        _add_text_paragraph(
            doc,
            _strip_label(block.text, "易错点|易错"),
            bold_label="易错：",
        )
        return
    if kind == BlockKind.SUMMARY:
        _add_text_paragraph(
            doc,
            _strip_label(block.text, "本节小结|小结"),
            bold_label="小结：",
        )
        return
    if kind == BlockKind.QUOTE:
        _add_text_paragraph(doc, block.text, italic=True)
        return
    table_match = _PIPE_TABLE.search(block.text or "")
    if table_match:
        before = (block.text or "")[:table_match.start()].strip()
        after = (block.text or "")[table_match.end():].strip()
        if before:
            _add_text_paragraph(doc, before)
        _add_md_table(doc, table_match.group(0))
        if after:
            _add_text_paragraph(doc, after)
        return
    _add_text_paragraph(doc, block.text)


def _add_section(doc, section: LectureSection, base_dir: Path) -> None:
    doc.add_heading(_plain(section.title), level=1)
    for block in section.blocks:
        _add_block(doc, block, base_dir)
    if section.summary:
        _add_text_paragraph(doc, section.summary, bold_label="本节小结：")
    _add_source_line(doc, section.source_refs)


def _add_closing(doc, spec: LectureSpec) -> None:
    doc.add_heading("结语", level=1)
    text = (spec.closing.text or "").replace("\\n", "\n")
    parts = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    for part in parts or [text]:
        _add_text_paragraph(doc, part)


def _add_field(paragraph, instruction: str, placeholder: str = "1") -> None:
    """插入一个简单的 Word 域（PAGE / NUMPAGES）。"""
    begin_run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin_run._r.append(begin)

    instruction_run = paragraph.add_run()
    instruction_text = OxmlElement("w:instrText")
    instruction_text.set(qn("xml:space"), "preserve")
    instruction_text.text = f" {instruction} "
    instruction_run._r.append(instruction_text)

    separate_run = paragraph.add_run()
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    separate_run._r.append(separate)

    _style_footer_run(paragraph.add_run(placeholder))

    end_run = paragraph.add_run()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run._r.append(end)


def _style_footer_run(run, size: float = 8.0) -> None:
    run.font.size = Pt(size)
    run.font.color.rgb = _MUTED


def _add_footer(doc, spec: LectureSpec) -> None:
    footer = doc.sections[0].footer
    footer.is_linked_to_previous = False
    footer_paragraph = footer.paragraphs[0]
    footer_paragraph.style = "Footer"
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_paragraph.paragraph_format.space_after = Pt(0)
    footer_text = (
        f"本资料由 {spec.footer.agent_name} 智能体生成，可涵盖《{spec.footer.material_label}》"
        f"约 {spec.footer.coverage_percent:g}% 的内容；{spec.footer.disclaimer}"
    )
    _style_footer_run(footer_paragraph.add_run(footer_text))

    ai_paragraph = footer.add_paragraph()
    ai_paragraph.style = "Footer"
    ai_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ai_paragraph.paragraph_format.space_before = Pt(0)
    _style_footer_run(ai_paragraph.add_run("AI 辅助生成 · 已做机器质量检查；具体内容以原始资料为准。"))

    page_paragraph = footer.add_paragraph()
    page_paragraph.style = "Footer"
    page_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    page_paragraph.paragraph_format.space_before = Pt(0)
    _style_footer_run(page_paragraph.add_run("第 "))
    _add_field(page_paragraph, "PAGE")
    _style_footer_run(page_paragraph.add_run(" 页 / 共 "))
    _add_field(page_paragraph, "NUMPAGES")
    _style_footer_run(page_paragraph.add_run(" 页"))




def _force_cjk_fonts(document) -> None:
    """给每个有文字的 run 写显式 ascii/hAnsi/eastAsia，避免主题字体在 Word/LibreOffice 里回落成方框。"""
    def walk(paragraphs):
        for p in paragraphs:
            style = (p.style.name or "") if p.style is not None else ""
            font = "Arial Unicode MS"
            for run in p.runs:
                if not run.text:
                    continue
                run.font.name = font
                rpr = run._element.get_or_add_rPr()
                rfonts = rpr.find(qn("w:rFonts"))
                if rfonts is None:
                    rfonts = OxmlElement("w:rFonts")
                    rpr.insert(0, rfonts)
                for key in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                    rfonts.set(qn(key), font)
                for key in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                    if rfonts.get(qn(key)) is not None:
                        del rfonts.attrib[qn(key)]

    walk(document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                walk(cell.paragraphs)
    for section in document.sections:
        walk(section.header.paragraphs)
        walk(section.footer.paragraphs)


def _ensure_docx_templates() -> None:
    """PyInstaller 把 docx 数据放在 Resources，而 python-docx 从 Frameworks 读；补一次。"""
    try:
        import docx
        target = Path(docx.__file__).resolve().parent / "templates"
        # PyInstaller 的模块是虚拟路径；python-docx 用 `parts/../templates`，
        # 因此必须保证真实文件系统里存在 parts 目录。
        (target.parent / "parts").mkdir(parents=True, exist_ok=True)
        if (target / "default.docx").is_file() and (target / "default-footer.xml").is_file():
            return
        candidates = []
        if getattr(sys, "_MEIPASS", None):
            candidates.append(Path(sys._MEIPASS) / "docx" / "templates")
        if getattr(sys, "executable", None):
            candidates.append(Path(sys.executable).resolve().parents[1] / "Resources" / "docx" / "templates")
        candidates.append(Path(docx.__file__).resolve().parents[2] / "Resources" / "docx" / "templates")
        for src in candidates:
            if (src / "default.docx").is_file():
                target.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, target, dirs_exist_ok=True)
                return
        raise FileNotFoundError(f"docx 模板缺失：{target}")
    except Exception:
        # 让调用方给出明确错误，而不是生成半成品文件
        raise


def write_docx(spec: LectureSpec, out_path: str | Path, *, base_dir: str | Path) -> Path:
    """把 LectureSpec 渲染为原生 .docx，返回实际写入路径。"""
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    base = Path(base_dir).expanduser()
    _ensure_docx_templates()

    document = Document()
    _configure_document(document, spec)

    _add_header(document, spec)
    _add_summary(document, spec)
    _add_toc(document, spec)

    if spec.chapter_title:
        chapter = document.add_heading(_plain(spec.chapter_title), level=0)
        chapter.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for section in spec.sections:
        _add_section(document, section, base)

    _add_closing(document, spec)
    _add_footer(document, spec)
    _force_cjk_fonts(document)

    document.save(str(target))
    return target
