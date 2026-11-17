"""LaTeX/XeLaTeX publication backend: native math, CJK, figures."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from tfv2.domain.lecture import LectureSpec


_UNICODE = {
    "β": r"$\beta$", "α": r"$\alpha$", "γ": r"$\gamma$", "μ": r"$\mu$",
    "π": r"$\pi$", "≥": r"$\geq$", "≤": r"$\leq$", "≈": r"$\approx$",
    "×": r"$\times$", "·": r"$\cdot$", "∞": r"$\infty$",
    "₀": r"$_0$", "₁": r"$_1$", "₂": r"$_2$", "₃": r"$_3$",
    "⁻": r"$^-$", "¹": r"$^1$", "²": r"$^2$", "³": r"$^3$",
}


def _esc(s: str) -> str:
    t = str(s or "")
    t = t.replace("\\", r"\textbackslash{}")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_"),
                 ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"),
                 ("^", r"\textasciicircum{}")):
        t = t.replace(a, b)
    return t


def _inline(s: str) -> str:
    parts = re.split(r"(\$\$.*?\$\$|\$[^$]*\$)", _strip_tags(str(s or "")), flags=re.S)
    out = []
    for i, part in enumerate(parts):
        if i % 2:
            out.append(part)
        else:
            out.append(_esc(part))
    return "".join(out)


def _strip_tags(s: str) -> str:
    return re.sub(r"\\tag\{([^{}]*)\}", r"\\quad(\1)", s or "")


def _formula(s: str) -> str:
    t = _strip_tags(str(s or "").strip())
    if not t:
        return ""
    if t.count("$") >= 2:
        return _inline(t)
    return r"\[" + t + r"\]"


def _figure(block, root: Path) -> str:
    fig = block.figure
    path = str(fig.asset_path or "").replace("\\", "/")
    if not path:
        return ""
    return (r"\begin{figure}[htbp]\centering" + "\n" +
            r"\includegraphics[width=0.82\linewidth]{\detokenize{" + str((root / path).resolve()) + "}}" + "\n" +
            r"\caption{" + _esc(fig.caption) + r"}" + "\n" +
            r"\end{figure}")


def _block(block, root: Path) -> str:
    kind = str(getattr(block.kind, "value", block.kind))
    if kind == "figure":
        return _figure(block, root)
    text = str(block.text or "")
    if kind == "formula":
        return _formula(text)
    label = {"example": "例题", "pitfall": "易错", "summary": "小结", "claim": "要点"}.get(kind, "")
    body = _inline(text)
    if label:
        return r"\begin{quote}\textbf{【" + label + r"】}" + body + r"\end{quote}"
    return body + "\n"


def render_latex(spec: LectureSpec, path: str | Path, *, root: str | Path) -> Path:
    root = Path(root).resolve()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        r"\documentclass[UTF8,fontset=mac,11pt]{ctexart}",
        r"\usepackage[a4paper,margin=2cm]{geometry}",
        r"\usepackage{amsmath,amssymb,graphicx,xcolor,hyperref}",
        r"\usepackage{booktabs}",
        r"\usepackage{newunicodechar}",
        r"\newunicodechar{β}{\ensuremath{\beta}}",
        r"\newunicodechar{α}{\ensuremath{\alpha}}",
        r"\newunicodechar{γ}{\ensuremath{\gamma}}",
        r"\newunicodechar{μ}{\ensuremath{\mu}}",
        r"\newunicodechar{π}{\ensuremath{\pi}}",
        r"\newunicodechar{≥}{\ensuremath{\geq}}",
        r"\newunicodechar{≤}{\ensuremath{\leq}}",
        r"\newunicodechar{≈}{\ensuremath{\approx}}",
        r"\newunicodechar{×}{\ensuremath{\times}}",
        r"\newunicodechar{·}{\ensuremath{\cdot}}",
        r"\newunicodechar{∞}{\ensuremath{\infty}}",
        r"\newunicodechar{₀}{\ensuremath{_0}}",
        r"\newunicodechar{₁}{\ensuremath{_1}}",
        r"\newunicodechar{₂}{\ensuremath{_2}}",
        r"\newunicodechar{₃}{\ensuremath{_3}}",
        r"\graphicspath{{" + str(root).replace("\\", "/") + r"/}}",
        r"\setlength{\parskip}{6pt}",
        r"\setlength{\parindent}{0pt}",
        r"\title{" + _esc(spec.header.title) + "}",
        r"\author{" + _esc(spec.header.course) + "}",
        r"\date{" + _esc(spec.header.generated_at) + "}",
        r"\begin{document}",
        r"\maketitle",
        r"\tableofcontents",
        r"\newpage",
    ]
    for sec in spec.sections:
        lines.append(r"\section*{" + _esc(sec.title) + "}")
        if getattr(sec, "objectives", None):
            lines.append(r"\textbf{本节目标}" + r"\begin{itemize}")
            lines += [r"\item " + _inline(x) for x in sec.objectives]
            lines.append(r"\end{itemize}")
        if getattr(sec, "key_terms", None):
            lines.append(r"\textbf{关键术语：}" + "；".join(_esc(x) for x in sec.key_terms))
        for block in sec.blocks:
            piece = _block(block, root)
            if piece:
                lines.append(piece)
        if getattr(sec, "self_test", None):
            lines.append(r"\textbf{自测}" + r"\begin{enumerate}")
            lines += [r"\item " + _inline(x) for x in sec.self_test]
            lines.append(r"\end{enumerate}")
        refs = []
        for ref in sec.source_refs:
            refs.extend(range(ref.page_start, (ref.page_end or ref.page_start) + 1))
        if refs:
            lines.append(r"\textcolor{gray}{\small 出处：第 " + "、".join(map(str, sorted(set(refs)))) + " 页}")
    lines.append(r"\end{document}")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def compile_latex(tex_path: str | Path, pdf_path: str | Path, *, root: str | Path) -> tuple[bool, str]:
    tex = Path(tex_path)
    pdf = Path(pdf_path)
    cmd = ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
           f"-output-directory={tex.parent}", str(tex)]
    log = ""
    for _ in range(2):
        try:
            proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=180)
            log = (proc.stdout or "") + (proc.stderr or "")
            if proc.returncode != 0:
                return False, log[-4000:]
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"
    built = tex.with_suffix(".pdf")
    if not built.is_file():
        return False, log[-2000:]
    if built.resolve() != pdf.resolve():
        import shutil
        shutil.copyfile(built, pdf)
    return True, ""
