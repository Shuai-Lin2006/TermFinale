"""Deterministic page facts: what a section must cover, extracted without an LLM."""
from __future__ import annotations

import re

_DEF = re.compile(r"(是指|称为|定义为|定义|叫做|即)")
_FORMULA = re.compile(r"(\$[^$]+\$|\$\$.+?\$\$|=|公式|定理|定律)")
_CONCLUSION = re.compile(r"(因此|所以|结论|可见|表明|说明|可知)")
_PITFALL = re.compile(r"(注意|易错|不能|避免|切勿|误区|错误)")
_FIG = re.compile(r"(图\s*\d+|表\s*\d+|如图|如下表|特性曲线|电路图)")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def extract_page_facts(text: str, *, limit: int = 5) -> dict:
    out = {"definitions": [], "formulas": [], "conclusions": [], "pitfalls": [], "figures": []}
    seen = {k: set() for k in out}
    for line in (text or "").splitlines():
        for raw in re.split(r"(?<=[。；;！？!?])", line):
            s = _clean(raw)
            if len(s) < 10 or len(s) > 300:
                continue
            for key, pat in (("definitions", _DEF), ("figures", _FIG),
                             ("formulas", _FORMULA), ("conclusions", _CONCLUSION),
                             ("pitfalls", _PITFALL)):
                if len(out[key]) < limit and pat.search(s) and s not in seen[key]:
                    out[key].append(s)
                    seen[key].add(s)
    return out


def facts_packet(pages: list[tuple[int, str]], *, limit: int = 4) -> str:
    parts = []
    for no, text in pages:
        f = extract_page_facts(text)
        lines = []
        for label, key in (("定义", "definitions"), ("公式", "formulas"),
                           ("结论", "conclusions"), ("易错", "pitfalls"), ("图表", "figures")):
            for x in f[key][:limit]:
                lines.append(f"- {label}: {x[:220]}")
        if lines:
            parts.append(f"【第{no}页事实】\n" + "\n".join(lines))
    return "\n\n".join(parts)
