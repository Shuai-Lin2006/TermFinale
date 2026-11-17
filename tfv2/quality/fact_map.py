"""Deterministic fact-to-block coverage; no LLM judge in this layer."""
from __future__ import annotations

import re
from pathlib import Path

from tfv2.authoring.page_facts import extract_page_facts


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{2,}", s or ""))


def facts_for_pages(page_text: dict[int, str], pages: list[int], *, per_page: int = 5) -> list[dict]:
    out = []
    for p in pages:
        f = extract_page_facts(page_text.get(p, ""))
        picked = []
        for key in ("definitions", "formulas", "conclusions", "pitfalls", "figures"):
            for x in f.get(key) or []:
                if x not in picked:
                    picked.append(x)
                if len(picked) >= per_page:
                    break
            if len(picked) >= per_page:
                break
        for i, text in enumerate(picked):
            out.append({"id": f"p{p}-f{i}", "page": p, "kind": key, "text": text})
    return out


def map_facts(facts: list[dict], sections) -> dict:
    """Bind every fact to the block with the strongest lexical overlap."""
    blocks = []
    for sec in sections:
        for b in getattr(sec, "blocks", sec.get("blocks", []) if isinstance(sec, dict) else []):
            text = b.text if hasattr(b, "text") else b.get("text", "")
            refs = b.source_refs if hasattr(b, "source_refs") else b.get("source_refs", [])
            pages = set()
            for r in refs or []:
                start = r.page_start if hasattr(r, "page_start") else r.get("page_start")
                end = r.page_end if hasattr(r, "page_end") else r.get("page_end")
                pages.update(range(int(start), int(end or start) + 1))
            blocks.append({"id": b.id if hasattr(b, "id") else b.get("id"), "text": text or "", "pages": pages})
    out = []
    for fact in facts:
        ft = _tokens(fact["text"])
        best = None
        best_score = 0
        for b in blocks:
            if fact["page"] not in b["pages"]:
                continue
            score = len(ft & _tokens(b["text"]))
            if fact["text"][:18] in b["text"]:
                score += 10
            if score > best_score:
                best, best_score = b, score
        mapped = best is not None and (best_score >= 2 or fact["text"][:18] in best["text"])
        out.append({**fact, "block_id": best["id"] if mapped else None,
                    "score": best_score, "status": "covered" if mapped else "missing"})
    return {"facts": out, "total": len(out),
            "covered": sum(1 for x in out if x["status"] == "covered"),
            "coverage": round(sum(1 for x in out if x["status"] == "covered") / max(1, len(out)), 3)}


def save_map(result: dict, path: str | Path) -> None:
    Path(path).write_text(__import__("json").dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
