"""跨资料统一的页单元：先判页型，再决定文字/影像/表格/公式处理。"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


PRIVATE_RE = re.compile(r"[\ue000-\uf8ff]")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
FORMULA_HINTS = set("∫∑∏√∂∇≈≠≤≥∞±×÷∈∉⊂⊃∪∩∀∃→⇒⇔αβγδεζηθλμνξπρστφχψωΓΔΘΛΞΠΣΦΨΩ")


def clean_text(value: str) -> str:
    text = str(value or "")
    text = PRIVATE_RE.sub("", text)
    text = CONTROL_RE.sub("", text)
    text = "".join(ch for ch in text if not (unicodedata.category(ch).startswith("C") and ch not in "\n\t"))
    return re.sub(r"[ \t]+", " ", text).strip()


def classify_page(text: str) -> str:
    raw = str(text or "")
    cleaned = clean_text(raw)
    if not cleaned.strip():
        return "image"
    if PRIVATE_RE.search(raw) or CONTROL_RE.search(raw):
        return "image"
    if sum(1 for ch in cleaned if ch in FORMULA_HINTS) >= 3 or cleaned.count("$") >= 4:
        return "formula"
    lines = [x for x in cleaned.splitlines() if x.strip()]
    if len(lines) >= 4 and sum(1 for x in lines if x.count("|") >= 2) >= 2:
        return "table"
    return "text"


@dataclass
class PageUnit:
    page_no: int
    kind: str
    text: str
    image: str | None = None
    tables: list[dict] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)


def build_page_unit(page_no: int, text: str, image: str | None = None) -> PageUnit:
    kind = classify_page(text)
    cleaned = clean_text(text)
    if kind == "image":
        return PageUnit(page_no=page_no, kind="image", text="", image=image)
    if kind == "formula":
        return PageUnit(page_no=page_no, kind="formula", text=cleaned, image=image)
    if kind == "table":
        return PageUnit(page_no=page_no, kind="table", text=cleaned, tables=[{"raw": cleaned}], image=image)
    return PageUnit(page_no=page_no, kind="text", text=cleaned, image=image)
