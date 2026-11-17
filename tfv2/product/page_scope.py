"""Page-range scope: only read/copy the pages the user selected."""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf


class ScopeError(ValueError):
    pass


def parse(spec: str, total: int) -> list[int]:
    total = int(total)
    if total <= 0:
        raise ScopeError("资料没有页")
    text = str(spec or "").strip().lower()
    if text in ("", "all", "全部"):
        return list(range(1, total + 1))
    pages: list[int] = []
    for part in re.split(r"[,，、\s]+", text):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*[-~—]\s*(\d+)", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > b:
                raise ScopeError(f"页码范围反了：{part}")
            pages.extend(range(a, b + 1))
        elif part.isdigit():
            pages.append(int(part))
        else:
            raise ScopeError(f"无法识别的页码：{part}")
    pages = sorted(set(pages))
    if not pages or pages[0] < 1 or pages[-1] > total:
        raise ScopeError(f"页码必须在 1..{total}")
    return pages


def slice_pdf(source: str | Path, out: str | Path, spec: str) -> dict:
    src = Path(source)
    doc = pymupdf.open(str(src))
    try:
        pages = parse(spec, len(doc))
        target = pymupdf.open()
        for p in pages:
            target.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
        target.save(str(out))
        target.close()
        return {"source": str(src), "out": str(out), "pages": pages,
                "page_count": len(pages), "original_pages": len(doc)}
    finally:
        doc.close()
