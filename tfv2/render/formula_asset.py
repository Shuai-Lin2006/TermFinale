"""Formula assets: classify, render, and never emit raw LaTeX.

A formula is not just a string. The asset keeps the original, a subject kind,
the Typst representation and a deterministic readable fallback. Renderers can
be replaced later (KaTeX/mhchem/RDKit) without changing lecture authoring.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from tfv2.render.typst_math import convert_math

_STRUCTURE_RE = re.compile(r"\\(chemfig|schemestart|schemebegin)\b")
_CHEM_RE = re.compile(r"\\(ce|chemfig|schemestart|schemebegin)\b")
_PHYS_RE = re.compile(r"\\(vec|hat|dot|ddot|bar|SI|hbar|partial|nabla)\b")
_UNKNOWN_CMD_RE = re.compile(r"\\[A-Za-z]+")


@dataclass
class FormulaAsset:
    latex: str
    kind: str = "math"          # math / physics / chemistry / structure
    renderer: str = "typst"     # typst / source_image / readable
    typst: str = ""
    display: str = ""           # guaranteed human-readable fallback
    status: str = "ok"          # ok / fallback
    error: str = ""
    source: dict[str, Any] = field(default_factory=dict)

    @property
    def has_raw_latex(self) -> bool:
        return bool(_UNKNOWN_CMD_RE.search(self.display)) or bool(_UNKNOWN_CMD_RE.search(self.typst))


def classify_formula(latex: str) -> str:
    text = str(latex or "")
    if _STRUCTURE_RE.search(text):
        return "structure"
    if _CHEM_RE.search(text):
        return "chemistry"
    if _PHYS_RE.search(text):
        return "physics"
    return "math"


def readable_fallback(latex: str) -> str:
    """Keep the meaning visible without leaking TeX commands."""
    s = str(latex or "").strip().strip("$").strip()
    s = re.sub(r"\\(?:ce|mathrm|text|operatorname)\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\(?:frac|dfrac|tfrac)\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", s)
    s = re.sub(r"\\sqrt\{([^{}]*)\}", r"√(\1)", s)
    s = s.replace("\\left", "").replace("\\right", "")
    s = re.sub(r"\\([A-Za-z]+)", r"\1", s)
    s = s.replace("{", "(").replace("}", ")")
    s = s.replace("_", "_").replace("^", "^")
    s = re.sub(r"\s+", " ", s).strip()
    return s or "公式"


def build_formula_asset(latex: str, *, source: dict[str, Any] | None = None) -> FormulaAsset:
    raw = str(latex or "").strip()
    body = raw.strip("$").strip()
    kind = classify_formula(body)
    asset = FormulaAsset(latex=raw, kind=kind, source=source or {})
    asset.display = readable_fallback(body)
    if kind == "structure":
        asset.renderer = "source_image"
        asset.display = "【化学结构式：优先使用资料原图】"
        asset.status = "fallback"
        return asset
    try:
        typst = convert_math(body)
        asset.typst = typst
        if not typst.strip():
            raise ValueError("empty conversion")
        if _UNKNOWN_CMD_RE.search(typst):
            raise ValueError("residual TeX command")
        asset.renderer = "typst"
        return asset
    except Exception as exc:
        asset.renderer = "readable"
        asset.status = "fallback"
        asset.error = str(exc)
        return asset


def assets_from_text(text: str) -> list[FormulaAsset]:
    out = []
    for m in re.finditer(r"\$\$(.+?)\$\$|\$(.+?)\$", str(text or ""), re.S):
        body = m.group(1) if m.group(1) is not None else m.group(2)
        out.append(build_formula_asset(body))
    return out


def collect_formula_assets(spec) -> list[FormulaAsset]:
    out: list[FormulaAsset] = []
    for sec in getattr(spec, "sections", []) or []:
        for block in getattr(sec, "blocks", []) or []:
            kind = str(getattr(block.kind, "value", block.kind))
            if kind == "formula":
                out.append(build_formula_asset(block.text or ""))
            else:
                out.extend(assets_from_text(block.text or ""))
    return out


def formula_report_markdown(assets: list[FormulaAsset]) -> str:
    lines = ["# 公式资产报告", "", f"- 公式数：{len(assets)}",
             f"- Typst 可渲染：{sum(1 for x in assets if x.renderer == 'typst')}",
             f"- 回退：{sum(1 for x in assets if x.status != 'ok')}", ""]
    lines += ["| 类型 | 渲染器 | 状态 | 公式 |", "|---|---|---|---|"]
    for x in assets:
        display = (x.display or x.latex).replace("|", "\\|")
        lines.append(f"| {x.kind} | {x.renderer} | {x.status} | `{display[:100]}` |")
    return "\n".join(lines) + "\n"
