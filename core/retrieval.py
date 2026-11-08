"""课程级页索引与检索：让 AI 回答前先找到资料页，而不是只看选中片段。"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

PAGE_HEADER_RE = re.compile(r"》\s*第\s*(\d+)\s*页】")
IMAGE_RE = re.compile(r"\[\[\[IMAGE:.*?\]\]\]", re.S)


def _norm(text: str) -> str:
    text = IMAGE_RE.sub(" ", text or "")
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text)


def _grams(text: str) -> set[str]:
    t = _norm(text)
    if len(t) < 2:
        return {t} if t else set()
    return {t[i:i + 2] for i in range(len(t) - 1)}


@dataclass
class PageDoc:
    page: int
    source: str
    text: str


def build_index(pages: list[str], source: str = "") -> list[PageDoc]:
    out = []
    for i, block in enumerate(pages or [], 1):
        m = PAGE_HEADER_RE.search(block or "")
        n = int(m.group(1)) if m else i
        out.append(PageDoc(n, source, block or ""))
    return out


def search(index: list[PageDoc], query: str, top_k: int = 4) -> list[dict]:
    q = _grams(query)
    if not q or not index:
        return []
    scored = []
    for doc in index:
        g = _grams(doc.text)
        if not g:
            continue
        inter = len(q & g)
        if not inter:
            continue
        # 长问题只重合一个二字词，多半是“函数/数学”这种噪声，不硬凑
        if len(q) >= 3 and inter < 2:
            continue
        score = inter / math.sqrt(len(q) * len(g))
        # 命中连续词/更长重合加权
        if len(q & g) >= 2:
            score *= 1.15
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, doc in scored[:top_k]:
        clean = re.sub(r"\s+", " ", IMAGE_RE.sub("", doc.text)).strip()
        out.append({"page": doc.page, "source": doc.source,
                    "score": round(score, 4), "text": clean[:1600]})
    return out
