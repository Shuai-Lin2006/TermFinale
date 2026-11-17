"""Fact curation: drop figure-only/duplicate/noise before planning."""
from __future__ import annotations

import re

from .model import Fact, FactKind

_FIG_ONLY = re.compile(r"^\s*(如图|根据图|由图|图\s*\d|表\s*\d|电路如图|图中)")
_WEIGHT = {FactKind.DEFINITION: 3, FactKind.FORMULA: 3, FactKind.PITFALL: 3,
           FactKind.CONCLUSION: 2, FactKind.FIGURE: 1}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def curate_facts(facts: list[Fact], *, per_page: int = 8) -> list[Fact]:
    out: list[Fact] = []
    seen: set[str] = set()
    by_page: dict[int, list[Fact]] = {}
    for f in facts:
        text = _norm(f.text)
        if len(text) < 14:
            continue
        if _FIG_ONLY.match(text) and len(text) < 60:
            continue
        key = re.sub(r"[^\w\u4e00-\u9fff]", "", text)[:80]
        if key in seen:
            continue
        seen.add(key)
        f = f.model_copy(update={"text": text})
        by_page.setdefault(f.page, []).append(f)
    for page in sorted(by_page):
        rows = sorted(by_page[page], key=lambda f: (-_WEIGHT.get(f.kind, 1), -len(f.text)))
        out.extend(rows[:per_page])
    return sorted(out, key=lambda f: (f.page, f.fact_id))
