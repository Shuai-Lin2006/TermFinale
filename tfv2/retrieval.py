"""轻量本地检索：给讲义 AI 提供可引用的段落，不依赖外部向量库。"""
from __future__ import annotations

import re
from collections import Counter
from math import log

from pydantic import BaseModel, Field

from tfv2.domain.lecture import LectureSection

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")
_STOP = set("的 了 是 在 和 与 及 或 有 没有 这 那 一个 一种 怎么 为什么 什么 可以 如何 请 解释 一下".split())
_LATEX_TEXT_RE = re.compile(r"\\(?:text|mathrm|mathbf|operatorname)\{([^{}]*)\}")
_LATEX_CMD_RE = re.compile(r"\\[A-Za-z]+")
_LATEX_SPACE_RE = re.compile(r"\\[,;:! ]")


def _normalize_for_search(text: str) -> str:
    """把 LaTeX 单位/命令还原成可检索文字。

    讲义里写 ``$9\\,\\text{mA}$``，直接分词会变成 9/text/ma，
    学生问“9mA 例题”反而检索不到；这里先还原成 ``9mA``。
    """
    text = _LATEX_TEXT_RE.sub(r"\1", text or "")
    text = _LATEX_SPACE_RE.sub("", text)
    text = _LATEX_CMD_RE.sub(" ", text)
    return text.replace("$", " ")


class Chunk(BaseModel):
    id: str
    section: str
    anchor: str
    pages: list[int]
    text: str
    score: float = 0.0


class RetrievalIndex(BaseModel):
    artifact_id: str
    chunks: list[Chunk] = Field(default_factory=list)


def _tokens(text: str) -> list[str]:
    raw = [x.lower() for x in _TOKEN_RE.findall(_normalize_for_search(text))]
    out: list[str] = []
    for x in raw:
        if x not in _STOP:
            out.append(x)
    # 中文相邻二字也作为词，提升“张力/构象”这类短查询
    chars = [x for x in raw if len(x) == 1 and "\u4e00" <= x <= "\u9fff"]
    out.extend(chars[i] + chars[i + 1] for i in range(len(chars) - 1))
    return out


def build_index(artifact_id: str, sections: list[LectureSection]) -> RetrievalIndex:
    chunks: list[Chunk] = []
    for sec in sections:
        pages = sorted({p for r in sec.source_refs for p in range(r.page_start, (r.page_end or r.page_start) + 1)})
        for block in sec.blocks:
            if block.kind.value == "figure":
                continue
            text = (block.text or "").strip()
            if not text:
                continue
            bp = sorted({p for r in block.source_refs for p in range(r.page_start, (r.page_end or r.page_start) + 1)}) or pages
            # 长段切块，避免一次塞太多
            for i in range(0, len(text), 700):
                part = text[i:i + 700]
                chunks.append(Chunk(
                    id=f"{sec.id}-{block.id}-{i//700}", section=sec.title,
                    anchor=sec.id, pages=bp, text=part,
                ))
    return RetrievalIndex(artifact_id=artifact_id, chunks=chunks)


def search(index: RetrievalIndex, query: str, *, top_k: int = 6, selection: str = "") -> list[Chunk]:
    qt = Counter(_tokens(query + " " + selection))
    if not qt:
        return index.chunks[:top_k]
    # IDF：像“9ma”“54”这样的稀有词要比“电容/电压”这类高频二字词更有分量，
    # 否则具体例题会被泛讲段落挤掉。
    doc_freq: Counter[str] = Counter()
    for chunk in index.chunks:
        for token in set(_tokens(chunk.text + " " + chunk.section)):
            doc_freq[token] += 1
    n_chunks = max(1, len(index.chunks))

    def idf(token: str) -> float:
        return log((n_chunks + 1) / (doc_freq[token] + 1)) + 1

    scored: list[Chunk] = []
    for chunk in index.chunks:
        text = chunk.text + " " + chunk.section
        ct = Counter(_tokens(text))
        score = sum(min(qt[t], 3) * ct[t] * idf(t) for t in qt)
        # 英文/数字词精确命中额外加权（如 9mA、54、18、τ）。
        score += 6 * sum(1 for t in qt if re.search(r"[a-z0-9]", t) and ct[t] > 0)
        title_tokens = Counter(_tokens(chunk.section))
        score += 5 * sum(min(qt[t], 2) * title_tokens[t] for t in qt)
        if selection and selection in chunk.text:
            score += 6
        if score > 0:
            scored.append(chunk.model_copy(update={"score": float(score)}))
    scored.sort(key=lambda x: (-x.score, x.id))
    return scored[:top_k]


def context(chunks: list[Chunk]) -> str:
    return "\n\n".join(
        f"[{c.section}｜第{','.join(map(str, c.pages))}页]\n{c.text}" for c in chunks
    )


def sources(chunks: list[Chunk]) -> list[dict]:
    seen: dict[str, dict] = {}
    for c in chunks:
        item = seen.setdefault(c.anchor, {"section": c.section, "anchor": c.anchor, "pages": []})
        item["pages"] = sorted(set(item["pages"]) | set(c.pages))
    return list(seen.values())


def expand_neighbors(index: RetrievalIndex, hits: list[Chunk], *, max_chunks: int = 10) -> list[Chunk]:
    """把命中段的相邻段一起带上，避免“检索到小节却漏掉下一段定义/公式”。

    相邻段只能占用剩余预算，不能把命中段本身挤掉。旧实现先加邻居再按
    document 顺序截断，像“9mA 例题”这种排在文档后部的命中会被前面的
    邻居挤出上下文，AI 就会误答“资料未覆盖”。
    """
    if len(hits) >= max_chunks:
        return hits[:max_chunks]
    order = {c.id: i for i, c in enumerate(index.chunks)}
    picked: dict[str, Chunk] = {c.id: c for c in hits}
    budget = max_chunks - len(picked)
    for c in hits:
        if budget <= 0:
            break
        i = order.get(c.id)
        if i is None:
            continue
        for j in (i - 1, i + 1):
            if budget <= 0:
                break
            if 0 <= j < len(index.chunks) and index.chunks[j].section == c.section:
                n = index.chunks[j]
                if n.id not in picked:
                    picked[n.id] = n
                    budget -= 1
    out = list(picked.values())
    out.sort(key=lambda x: order.get(x.id, 10**9))
    return out[:max_chunks]
