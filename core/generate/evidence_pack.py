"""证据句库：先把资料拆成可引用原句，再让写作层只能引用这些句子。

这是“先证据、后写作”的基础设施，不是生成后再补页码。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PAGE_HEADER_RE = re.compile(r"》\s*第\s*(\d+)\s*页】")
IMAGE_RE = re.compile(r"\[\[\[IMAGE:.*?\]\]\]", re.S)
AD_RE = re.compile(r"(?:QQ\s*群|公众号|蜂考|扫码|关注)")
MATERIAL_PREFIX_RE = re.compile(r"^【[^】]*(?:资料|权重)[^】]*】\s*")
FILE_HEADER_RE = re.compile(r"^【《[^》]+》[^】]*】\s*")
SPLIT_RE = re.compile(r"(?<=[。！？!?；;])\s*")
FOOTER_RE = re.compile(r"\s*\d+\\\d+\s*$")
IMAGE_CAPTION_RE = re.compile(r"\[\[\[IMAGE:.*?\|\s*图注:\s*(.*?)（第\s*(\d+)\s*页）\]\]\]", re.S)


@dataclass
class Evidence:
    eid: str
    page: int
    quote: str


def _clean(page: str) -> str:
    t = MATERIAL_PREFIX_RE.sub("", page or "")
    t = FILE_HEADER_RE.sub("", t)
    t = PAGE_HEADER_RE.sub("", t)
    t = FOOTER_RE.sub("", t)
    t = IMAGE_RE.sub("", t)
    lines = [ln.strip() for ln in t.splitlines() if ln.strip() and not AD_RE.search(ln)]
    return " ".join(lines)


def _good_quote(q: str) -> bool:
    q = (q or "").strip()
    if len(re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", q)) < 6:
        return False
    if re.search(r"[\uf000-\uf0ff]", q):
        return False
    words = re.findall(r"[A-Za-z]+", q)
    if len(words) >= 6 and sum(1 for w in words if len(w) == 1) / len(words) > 0.55:
        return False
    if q.count(" ") > 18 and len(q) < 60:
        return False
    return True


def build_pack(pages: list[str], max_per_page: int = 3, min_len: int = 12, max_len: int = 140) -> list[Evidence]:
    out: list[Evidence] = []
    for i, page in enumerate(pages or [], 1):
        m = PAGE_HEADER_RE.search(page or "")
        n = int(m.group(1)) if m else i
        for cm in IMAGE_CAPTION_RE.finditer(page or ""):
            cap = re.sub(r"\s+", " ", cm.group(1)).strip()
            cap_page = int(cm.group(2) or n)
            if len(cap) >= 6 and _good_quote(cap) and not any(cap == e.quote for e in out):
                out.append(Evidence(f"E{len(out) + 1}", cap_page, f"【图示】{cap}"))
        text = _clean(page)
        for sent in SPLIT_RE.split(text):
            sent = sent.strip(" \t")
            if len(sent) < min_len or len(sent) > max_len:
                continue
            if not _good_quote(sent):
                continue
            if sent.startswith(("图", "表", "注：")) and len(sent) < 20:
                continue
            out.append(Evidence(f"E{len(out) + 1}", n, sent))
            if sum(1 for e in out if e.page == n) >= max_per_page:
                break
        if not any(e.page == n for e in out):
            lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 10]
            for ln in lines[:max_per_page]:
                if _good_quote(ln):
                    out.append(Evidence(f"E{len(out) + 1}", n, ln[:max_len]))
    return out


def render_pack(pack: list[Evidence], max_items: int = 60) -> str:
    return "\n".join(f"[{e.eid}｜P.{e.page}] {e.quote}" for e in pack[:max_items])


def supported_by_quote(block: str, pack: list[Evidence], min_overlap: float = 0.5) -> bool:
    text = IMAGE_RE.sub("", block or "")
    for e in pack:
        if e.quote and e.quote in text:
            return True
    # 允许改写：与某条证据 2-gram 覆盖 ≥ min_overlap
    from core.retrieval import _grams  # 复用归一化
    bg = _grams(text)
    if not bg:
        return False
    for e in pack:
        qg = _grams(e.quote)
        if qg and len(bg & qg) / len(bg) >= min_overlap:
            return True
    return False


def filter_unsupported(markdown: str, pack: list[Evidence], min_overlap: float = 0.5) -> tuple[str, int, int]:
    """删掉没有证据支撑的自然段/要点；标题保留。返回 (文本, 保留段数, 删除段数)。"""
    parts = re.split(r"(\n\s*\n)", markdown or "")
    out: list[str] = []
    kept = dropped = 0
    for part in parts:
        if not part or part.isspace():
            out.append(part); continue
        if part.lstrip().startswith("#") or part.strip() in ("---", "***"):
            out.append(part); continue
        if len(re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", part)) < 12:
            out.append(part); continue
        if supported_by_quote(part, pack, min_overlap):
            out.append(part); kept += 1
        else:
            dropped += 1
    return "".join(out), kept, dropped
