"""Coverage ledger: every source page has a status, every module has a report.

This module is deterministic and free: it never calls an LLM. It answers the
first question before any expensive generation: did we actually see every page?
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pymupdf


def _page_status(page) -> dict:
    try:
        text = page.get_text("text") or ""
        chars = len(text.strip())
        images = len(page.get_images(full=True))
        drawings = len(page.get_drawings())
    except Exception as exc:
        return {"status": "failed", "chars": 0, "images": 0, "drawings": 0, "error": str(exc)}
    if chars >= 20 and images:
        status = "text_with_images"
    elif chars >= 20:
        status = "text"
    elif images:
        status = "image"
    elif drawings >= 3:
        status = "vector"
    else:
        status = "blank"
    return {"status": status, "chars": chars, "images": images, "drawings": drawings}


def scan_pdf(path: str | Path, *, max_pages: int | None = None) -> dict:
    """Build a page ledger. No OCR, no model call, no cost."""
    pdf = Path(path)
    doc = pymupdf.open(str(pdf))
    try:
        total = len(doc)
        limit = total if not max_pages else min(total, int(max_pages))
        pages = []
        counts: dict[str, int] = {}
        for i in range(limit):
            row = _page_status(doc[i])
            row["page"] = i + 1
            pages.append(row)
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        return {
            "material": pdf.name,
            "page_count": total,
            "scanned_pages": limit,
            "coverage_percent": round(limit / max(1, total) * 100, 2),
            "status_counts": counts,
            "failed_pages": [p["page"] for p in pages if p["status"] == "failed"],
            "blank_pages": [p["page"] for p in pages if p["status"] == "blank"],
            "pages": pages,
        }
    finally:
        doc.close()


def _cited_pages(doc: dict) -> set[int]:
    cited: set[int] = set()
    kind = str(doc.get("kind") or "")
    content = doc.get("content") or {}
    if kind == "exam":
        for sec in content.get("sections") or []:
            for q in sec.get("questions") or []:
                try:
                    cited.add(int(q.get("source_page")))
                except (TypeError, ValueError):
                    pass
    elif kind in ("extract_points", "extract_nouns", "extract_questions", "paper"):
        items = content.get("items") or content.get("questions") or []
        for item in items:
            for key in ("page", "source_page"):
                try:
                    p = int(item.get(key))
                except (TypeError, ValueError):
                    continue
                end = item.get("page_end") or p
                try:
                    cited.update(range(p, int(end) + 1))
                except (TypeError, ValueError):
                    cited.add(p)
    elif kind == "lecture":
        for sec in content.get("sections") or []:
            for block in sec.get("blocks") or []:
                for ref in block.get("source_refs") or []:
                    try:
                        cited.update(range(int(ref.get("page_start")), int(ref.get("page_end") or ref.get("page_start")) + 1))
                    except (TypeError, ValueError):
                        pass
    return {p for p in cited if p >= 1}


def module_coverage(doc: dict, page_count: int, *, require: bool = True) -> dict:
    cited = _cited_pages(doc)
    expected = set(range(1, page_count + 1))
    covered = expected & cited
    missing = sorted(expected - cited)
    return {
        "kind": str(doc.get("kind") or ""),
        "page_count": page_count,
        "pages_cited": sorted(cited),
        "pages_covered": len(covered),
        "coverage_percent": round(len(covered) / max(1, page_count) * 100, 2),
        "missing_pages": missing,
        "passed": bool(doc.get("content")) and (not require or not missing),
    }


def write_report(out_dir: str | Path, ledger: dict, modules: list[dict] | None = None, filename: str = "coverage_report.json") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "page_ledger": ledger,
        "modules": modules or [],
        "cost": {"llm_calls": 0, "note": "page ledger is deterministic and free"},
    }
    path = out / filename
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
