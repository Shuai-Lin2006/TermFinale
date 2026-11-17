"""资料标题层：把 MinerU/OCR 解析出的真实标题，变成讲义目录与融合章节。

为什么单独一层：
- 讲义目录以前靠正则从页文本里猜（“1.3.4 三极管的特性曲线”），遇到扫描件就完全失效；
- MinerU 能给出标题层级（# 的数量），这本该是目录的唯一可靠来源；
- 标题层必须能降级：没有 headings.json 时，调用方回落到页段/正则，不假装有目录。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_CHAPTER_ONLY = re.compile(r"^第\s*[一二三四五六七八九十百零\d]+\s*[章节篇]$")
_NUM_ONLY = re.compile(r"^\d+(?:\.\d+){0,3}$")
_CHAPTER_ANY = re.compile(r"^第\s*[一二三四五六七八九十百零\d]+\s*[章节篇]")
_LIST_LEVEL = re.compile(r"^\d+\s*[.、．)]\s*(?!\d)\S")    # “1. 输入特性”（不是 1.3.4）
_MULTI_LEVEL = re.compile(r"^\d+(?:\.\d+){1,3}\s*\S")     # “1.3.4”“2.1”这类章节编号


def load_headings(artifact_path: Path | None) -> list[dict]:
    """读产物目录里的 headings.json；没有就返回空列表（调用方负责降级）。"""
    if artifact_path is None:
        return []
    path = Path(artifact_path) / "headings.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = data.get("headings") if isinstance(data, dict) else data
    out: list[dict] = []
    for item in rows or []:
        try:
            page = int(item.get("page"))
            text = str(item.get("text") or "").strip()
        except Exception:
            continue
        if page < 1 or not text:
            continue
        out.append({"page": page, "level": int(item.get("level") or 1), "text": text})
    return out


def drop_item_headings(headings: list[dict]) -> list[dict]:
    """有真正的章节编号时，丢掉“1. 输入特性”这种列表项标题。

    教材/讲义里列表编号和章节编号混在一起；全都要会把“2. 输出特性”当成一章。
    """
    rows = list(headings or [])
    structural = [h for h in rows
                  if _CHAPTER_ANY.match(str(h.get("text") or "").strip())
                  or _MULTI_LEVEL.match(str(h.get("text") or "").strip())]
    if len(structural) < 3:
        return rows
    return [h for h in rows if not _LIST_LEVEL.match(str(h.get("text") or "").strip())]


def normalize_headings(headings: list[dict]) -> list[dict]:
    """合并“第二章”+“放大电路分析基础”这类被拆开的标题，并去掉连续重复。"""
    rows = sorted((dict(x) for x in drop_item_headings(headings)),
                  key=lambda x: (int(x["page"]), int(x.get("level") or 1)))
    merged: list[dict] = []
    i = 0
    while i < len(rows):
        cur = rows[i]
        text = cur["text"].strip()
        if (_CHAPTER_ONLY.match(text) or _NUM_ONLY.match(text)) and i + 1 < len(rows):
            nxt = rows[i + 1]
            gap = int(nxt["page"]) - int(cur["page"])
            if gap <= 1 and not _CHAPTER_ONLY.match(str(nxt["text"]).strip()):
                text = f"{text} {nxt['text'].strip()}"
                i += 1
        if merged and (text in merged[-1]["text"] or merged[-1]["text"].endswith(text)):
            i += 1
            continue
        if not merged or merged[-1]["text"] != text:
            merged.append({"page": int(cur["page"]), "level": int(cur.get("level") or 1), "text": text})
        i += 1
    return merged


def chapters_from_headings(headings: list[dict], chosen: list[int], *, chunk: int = 25) -> list[dict]:
    """按标题把选中页切成章节；每个章节 {"title", "pages"(原资料页码), "source_page"}。

    - 只按**每页第一个标题**切章（同页后续标题是小节，不另立章）；
    - 第一章之前的页归“开篇”；
    - 超长章节按 chunk 页拆开，标题带页码，避免目录里一节跨几百页。
    """
    if not chosen:
        return []
    chosen_set = set(int(p) for p in chosen)
    starts: list[tuple[int, str]] = []
    seen_pages: set[int] = set()
    for h in normalize_headings(headings):
        page = int(h["page"])
        if page not in chosen_set or page in seen_pages:
            continue
        starts.append((page, str(h["text"]).strip()))
        seen_pages.add(page)
    starts.sort()

    chapters: list[dict] = []
    ordered = sorted(chosen_set)
    if not starts:
        return _by_pages(ordered, chunk=chunk)

    first = starts[0][0]
    head = [p for p in ordered if p < first]
    if head:
        chapters.append({"title": f"开篇（第 {head[0]} 页起）", "pages": head, "source_page": head[0]})
    bounds = [s[0] for s in starts] + [10 ** 9]
    for idx, (page, title) in enumerate(starts):
        lo, hi = bounds[idx], bounds[idx + 1]
        pages = [p for p in ordered if lo <= p < hi]
        if not pages:
            continue
        for i in range(0, len(pages), chunk):
            part = pages[i:i + chunk]
            if i == 0:
                label = title
            else:
                label = f"{title} · 第 {part[0]}–{part[-1]} 页"
            chapters.append({"title": label, "pages": part, "source_page": part[0]})
    return chapters


def _by_pages(ordered: list[int], *, chunk: int = 25) -> list[dict]:
    out = []
    for i in range(0, len(ordered), chunk):
        part = ordered[i:i + chunk]
        title = (f"第 {part[0]} 页" if len(part) == 1 else f"第 {part[0]}–{part[-1]} 页")
        out.append({"title": title, "pages": part, "source_page": part[0]})
    return out
