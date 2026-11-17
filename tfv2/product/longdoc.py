"""Long-document chapter splitter.

Real 300-page textbooks often put a printed TOC near the front. We map that
TOC to *physical* pages, then prove every physical page belongs to exactly one
chapter. If no TOC exists we scan chapter headings; if neither exists we return
one honest "正文" section instead of inventing chapters.
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

_TOC = re.compile(r"^\s*((?:第\s*[一二三四五六七八九十百零\d]+\s*[章])|(?:\d+(?:\.\d+)*))\s+(.{2,80}?)\s*(?:\.{2,}|…{2,}|·{3,})\s*(\d{1,4})\s*$")
_HEAD = re.compile(r"^\s*((?:第\s*[一二三四五六七八九十百零\d]+\s*[章])|(?:\d+(?:\.\d+)*))\s+(.{2,80})$")


def _lines(text: str) -> list[str]:
    return [x.strip() for x in (text or "").splitlines() if x.strip()]


def _scan_toc(doc) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for i in range(min(30, len(doc))):
        for line in _lines(doc[i].get_text("text")):
            m = _TOC.match(line)
            if not m:
                continue
            page = int(m.group(3))
            if 1 <= page <= len(doc):
                entries.append((page, f"{m.group(1)} {m.group(2)}".strip()))
    # dedupe by page; keep first title
    out = []
    seen = set()
    for page, title in sorted(entries):
        if page in seen:
            continue
        seen.add(page)
        out.append((page, title))
    return out


def _scan_headings(doc) -> list[tuple[int, str]]:
    out = []
    for i in range(len(doc)):
        for line in _lines(doc[i].get_text("text")):
            m = _HEAD.match(line)
            if m and len(m.group(2)) <= 80:
                out.append((i + 1, f"{m.group(1)} {m.group(2)}".strip()))
                break
    return out


def _chapters(starts: list[tuple[int, str]], page_count: int) -> list[dict]:
    if not starts:
        return [{"title": "正文", "start": 1, "end": page_count}]
    # A TOC may start after a cover/preface; keep it as 前置内容.
    out: list[dict] = []
    if starts[0][0] > 1:
        out.append({"title": "前置内容", "start": 1, "end": starts[0][0] - 1})
    for i, (start, title) in enumerate(starts):
        end = starts[i + 1][0] - 1 if i + 1 < len(starts) else page_count
        if end < start:
            continue
        out.append({"title": title, "start": start, "end": end})
    return out


def split_pdf(path: str | Path) -> dict:
    path = Path(path)
    doc = pymupdf.open(str(path))
    try:
        page_count = len(doc)
        toc = _scan_toc(doc)
        if toc:
            starts, source = toc, "toc"
        else:
            starts, source = _scan_headings(doc), "heading"
            if not starts:
                source = "fallback"
        chapters = _chapters(starts, page_count)
        covered = []
        for c in chapters:
            covered.extend(range(c["start"], c["end"] + 1))
        if sorted(covered) != list(range(1, page_count + 1)):
            raise ValueError("章节没有完整覆盖 1..page_count")
        return {"page_count": page_count, "source": source, "chapters": chapters}
    finally:
        doc.close()
