"""Final text cleanup before rendering.

Two recurring failure modes:
- OCR/model emits raw LaTeX commands that the renderer prints literally;
- when source text is thin, the model fills the section with template lines
  ("本节目标 / 理解本节核心概念 / 关键术语 / 核心概念").
Both make a lecture look generated but unreadable.  Clean here, and reject a
section that has nothing substantive left.
"""
from __future__ import annotations

import re

_RAW_TEX = re.compile(r"\\(?:Rightarrow|rightarrow|mathrm|mathbf|qquad|quad|cdot|times|frac|dfrac|sqrt|left|right|begin|end|text|mathrm|,|;|:|!)")
_GENERIC = re.compile(
    r"^(本节目标|学习目标|理解本节核心概念|关键术语|核心概念|本章目标|考点|重点|难点|"
    r"本节介绍了|本节主要|综上所述|值得注意的是|通过学习本节|希望大家|同学们)[:：。!！\s]*$"
)
_GENERIC_INLINE = re.compile(r"理解本节核心概念|本节目标[:：]?\s*$|关键术语[:：]?\s*$|核心概念[:：]?\s*$")


def clean_text(text: str) -> str:
    t = str(text or "")
    # 字体私有区/替换符在 PDF 里会变成空白，不能留
    t = "".join("" if (0xE000 <= ord(ch) <= 0xF8FF or ch in "\ufffc\ufffd") else ch for ch in t)
    if "\\" in t or "$" in t:
        try:
            from tfv2.render.docx import _latex_to_text
            t = _latex_to_text(t)
        except Exception:
            t = t.replace("$", "").replace("\\", "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def is_generic(text: str) -> bool:
    t = clean_text(text)
    if not t:
        return True
    if _GENERIC.match(t):
        return True
    if len(t) <= 18 and _GENERIC_INLINE.search(t):
        return True
    return False


def clean_sections(sections) -> int:
    """Clean blocks in place; drop generic/duplicate blocks. Returns kept count."""
    kept = 0
    seen: set[str] = set()
    for sec in sections:
        blocks = list(getattr(sec, "blocks", []) or [])
        out = []
        for b in blocks:
            text = clean_text(getattr(b, "text", "") or "")
            if not text or is_generic(text):
                continue
            key = re.sub(r"\s+", "", text)[:80]
            if key in seen:
                continue
            seen.add(key)
            try:
                b.text = text
            except Exception:
                pass
            out.append(b)
            kept += 1
        try:
            sec.blocks = out
        except Exception:
            pass
    return kept
