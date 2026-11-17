"""Render a LectureSpec to Typst + PDF.

The HTML reader stays the primary UI. Typst is a publication backend: clean
page setup, outline, figures, textbook modules and converted math.
"""
from __future__ import annotations

import re
from pathlib import Path

from tfv2.domain.lecture import BlockKind, FigureRef, LectureSpec
from tfv2.render.formula_asset import build_formula_asset
from tfv2.render.typst_math import convert_math


def _q(s: str) -> str:
    return str(s or "").replace("\\", "\\\\").replace('"', '\\"')


def _txt(s: str) -> str:
    # #text("...") is literal content, so Typst markup characters are safe.
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return f'#text("{_q(s)}")' if s else ""


def _image_args(path: str) -> str:
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
        ratio = w / max(1, h)
        if ratio >= 1.6:
            return "width: 84%"
        if ratio >= 1.15:
            return "width: 72%"
        if ratio <= 0.65:
            return "height: 82mm"
        return "width: 58%"
    except Exception:
        return "width: 72%"


def _source_pages(refs) -> str:
    pages = []
    for ref in refs or []:
        pages.extend(range(ref.page_start, (ref.page_end or ref.page_start) + 1))
    return "、".join(map(str, sorted(set(pages))))


def _code_txt(s: str) -> str:
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return f'text("{_q(s)}")' if s else '""'


def _math_or_text(s: str) -> str:
    """Convert $...$ / $$...$$ inside prose; other text remains literal."""
    text = str(s or "")
    if "$" not in text:
        return _txt(text)
    out: list[str] = []
    pos = 0
    for m in re.finditer(r"\$\$(.+?)\$\$|\$(.+?)\$", text, re.S):
        out.append(_txt(text[pos:m.start()]))
        body = m.group(1) if m.group(1) is not None else m.group(2)
        asset = build_formula_asset(body)
        if asset.renderer == "typst" and asset.typst:
            out.append("$" + asset.typst + "$")
        else:
            out.append(_txt(asset.display))
        pos = m.end()
    out.append(_txt(text[pos:]))
    return "".join(out)


def _block(block) -> str:
    text = str(block.text or "")
    kind = str(getattr(block.kind, "value", block.kind))
    if kind == "figure" and block.figure is not None:
        fig = block.figure
        path = str(fig.asset_path or "").replace("\\", "/")
        img = f'image("{_q(path)}", {_image_args(path)})' if path else _code_txt("图片缺失")
        return f'#figure({img}, caption: {_code_txt(fig.caption)}, kind: image)'
    if kind == "formula":
        # A formula block often contains prose + several inline formulas.
        # Wrapping the whole block in one $...$ produces an unclosed delimiter.
        if text.count("$") >= 2 and not (text.strip().startswith("$$") and text.strip().endswith("$$")):
            return f"#par[{_math_or_text(text)}]"
        asset = build_formula_asset(text)
        if asset.renderer == "typst" and asset.typst:
            return "#block(fill: rgb(\"#f7f4fb\"), stroke: 0.4pt + purple, inset: 8pt, radius: 3pt)[#align(center)[$ " + asset.typst + " $]]"
        return "#align(center)[#text(fill: luma(80))[" + _txt(asset.display) + "]]"
    label = {"example": "例题", "pitfall": "易错", "summary": "小结", "claim": "要点"}.get(kind, "")
    content = _math_or_text(text)
    if label:
        palettes = {
            "例题": ("blue", "#eef6f8"),
            "易错": ("purple", "#f7f2fa"),
            "小结": ("green", "#f0f7f1"),
            "要点": ("blue", "#eef6f8"),
        }
        color, fill = palettes.get(label, ("blue", "#eef6f8"))
        return (f'#block(fill: rgb(\"{fill}\"), stroke: 0.5pt + {color}, inset: 11pt, radius: 4pt)'
                f'[#text(weight: \"bold\", fill: {color})[【{label}】] {content}]')
    return f"#par[{content}]"


def _section(sec) -> str:
    out = [f"#heading(level: 1)[{_txt(sec.title)}]"]
    if getattr(sec, "objectives", None):
        out.append("#block(fill: rgb(\"#eef6f8\"), stroke: 0.5pt + blue, inset: 9pt, radius: 3pt)[#text(weight: \"bold\", fill: blue)[本节目标]")
        out.append("#list(" + ", ".join(_code_txt(x) for x in sec.objectives) + ")]")
    if getattr(sec, "key_terms", None):
        out.append("#block(fill: rgb(\"#f0f7f1\"), stroke: 0.5pt + green, inset: 9pt, radius: 3pt)[#text(weight: \"bold\", fill: green)[关键术语] " +
                   "、".join(_txt(x) for x in sec.key_terms) + "]")
    for block in sec.blocks:
        piece = _block(block)
        if piece:
            out.append(piece)
    if getattr(sec, "self_test", None):
        out.append("#block(fill: rgb(\"#fbf7ef\"), stroke: 0.5pt + rgb(\"#b07a2a\"), inset: 10pt, radius: 4pt)[#text(weight: \"bold\", fill: rgb(\"#8a5a16\"))[自测]")
        out.append("#enum(" + ", ".join(_code_txt(x) for x in sec.self_test) + ")]")
    if sec.source_refs:
        pages = []
        for ref in sec.source_refs:
            pages.extend(range(ref.page_start, (ref.page_end or ref.page_start) + 1))
        pages = sorted(set(pages))
        out.append("#text(size: 8pt, fill: luma(100))[出处：" + _txt("第 " + "、".join(map(str, pages)) + " 页") + "]")
    out.append("#v(0.8cm)")
    return "\n".join(out)


def render_typst(spec: LectureSpec, path: str | Path, *, asset_root: str | Path | None = None) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "#let ink = rgb(\"#1f2933\")",
        "#let blue = rgb(\"#226f86\")",
        "#let green = rgb(\"#2f7d62\")",
        "#let purple = rgb(\"#6b4c9a\")",
        "#let soft = rgb(\"#f4f8f8\")",
        "#set page(fill: rgb(\"#fcfcfa\"), width: 210mm, height: 297mm, margin: (x: 18mm, top: 22mm, bottom: 20mm), numbering: none)",
        "#set text(font: (\"Songti SC\", \"PingFang SC\"), size: 11pt, fill: ink)",
        "#set page(header: align(right)[#text(size: 8pt, fill: luma(110))[" + _txt(spec.header.course) + "]], footer: context align(center)[#counter(page).display(\"1\")])",
        "#set par(justify: true, leading: 0.95em, spacing: 1.2em)",
        "#set heading(numbering: none)",
        "#show heading.where(level: 1): it => block(width: 100%, fill: rgb(\"#eaf4f6\"), inset: (x: 12pt, y: 7pt), radius: 4pt, above: 1.6em, below: 1em, breakable: false, stack(dir: ltr, box(width: 4pt, height: 1.2em, fill: blue), h(9pt), text(size: 18pt, weight: \"bold\", fill: ink, it.body)))",
        "#show heading.where(level: 2): it => block(above: 1.1em, below: 0.6em, breakable: false, text(size: 14pt, weight: \"bold\", fill: green, it.body))",
        "#set block(radius: 3pt)",
        "#set figure(supplement: [图], gap: 0.8em)",
        "#show heading: set block(breakable: false, above: 1.4em, below: 0.9em)",
        "#show figure: set block(breakable: false, above: 1em, below: 1em)",
        "",
        "#align(center)[#text(size: 24pt, weight: \"bold\")[" + _txt(spec.header.title) + "]]",
        f"#align(center)[#text(size: 10pt, fill: luma(100))[{_txt(spec.header.course)}]]",
        f"#v(0.3cm)#align(center)[{_txt('全量 · ' + str(spec.page_count) + ' 页 · 目标 ' + str(spec.header.target_score or 80) + ' 分')}]",
        "#v(0.5cm)",
        "#outline(title: [目录], depth: 2)",
        "#pagebreak()",
        f"#heading(level: 1)[{_txt('本资料讲什么')}]",
        "#par[" + _math_or_text(spec.summary.overview) + "]",
    ]
    if spec.summary.knowledge_map:
        lines.append("#heading(level: 2)[知识地图]")
        lines.append("#list(" + ", ".join(_code_txt(x) for x in spec.summary.knowledge_map) + ")")
    lines += ["#pagebreak()"]
    for sec in spec.sections:
        lines.append("#pagebreak(weak: true)")
        lines.append(_section(sec))
    if spec.closing and spec.closing.text:
        lines += ["#heading(level: 1)[结语]", "#par[" + _math_or_text(spec.closing.text) + "]"]
    if spec.sections:
        lines += ["#pagebreak()", "#heading(level: 1)[资料页码索引]",
                  "#table(columns: (1fr, 1fr), stroke: 0.5pt + luma(190), inset: 6pt,",
                  "[章节], [出处],"]
        for sec in spec.sections:
            pages = _source_pages(sec.source_refs)
            lines.append("[" + _txt(sec.title) + "], [" + _txt("第 " + pages + " 页" if pages else "未标注") + "],")
        lines.append(")")
    lines.append("#v(0.5cm)")
    lines.append("#text(size: 8pt, fill: luma(100))[" + _txt(spec.footer.disclaimer) + "]")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def find_typst() -> str | None:
    import shutil
    import sys
    candidates = [
        Path(__file__).resolve().parents[2] / "tools" / "typst",
        (Path(sys._MEIPASS) / "tools" / "typst") if getattr(sys, "_MEIPASS", None) else None,
        Path(sys.executable).resolve().parent.parent / "Frameworks" / "tools" / "typst",
        Path(sys.executable).resolve().parent / "tools" / "typst",
    ]
    for x in candidates:
        if x and x.is_file():
            return str(x)
    if shutil.which("typst"):
        return shutil.which("typst")
    if Path("/opt/homebrew/bin/typst").is_file():
        return "/opt/homebrew/bin/typst"
    return None


def compile_typst(typ_path: str | Path, pdf_path: str | Path, *, root: str | Path | None = None) -> tuple[bool, str]:
    import subprocess
    exe = find_typst()
    if not exe:
        return False, "typst CLI 未安装"
    cmd = [exe, "compile", str(typ_path), str(pdf_path)]
    if root:
        cmd[2:2] = ["--root", str(root)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.returncode == 0, (r.stderr or r.stdout)[-2000:]
