"""可测量的质量指标：不调模型，只用文本算。

为什么单独成模块：
- 讲义“好不好”以前只能靠人看；这里给三类可复现的数字：
  1. 重复句/模板句（注水检测）；
  2. 术语召回（讲义是否真的覆盖了资料里的核心名词）；
  3. 引用支持率（每个正文块引的页，到底支不支持这段话）。
- 指标函数必须是纯函数，评测脚本和单测共用，避免“脚本里一套、测试里一套”。
"""
from __future__ import annotations

import re
from collections import Counter

CJK = re.compile(r"[\u4e00-\u9fff]")
CJK_RUN = re.compile(r"[\u4e00-\u9fff]{2,}")
STOP = {
    "我们", "他们", "可以", "这个", "那个", "所以", "因为", "如果", "就是", "一个",
    "以及", "进行", "对于", "通过", "需要", "没有", "不是", "这样", "什么", "时候",
    "问题", "方法", "内容", "下面", "上面", "其中", "因此", "但是", "而且", "或者",
}


def sentences(text: str, *, min_len: int = 8) -> list[str]:
    parts = [x.strip() for x in re.split(r"[。！？!?；;\n]", str(text or "")) if x.strip()]
    return [x for x in parts if len(x) >= min_len]


def dup_sentence_ratio(texts: list[str]) -> float:
    norm = [re.sub(r"\s+", "", t) for t in texts if t and t.strip()]
    if not norm:
        return 0.0
    return round((len(norm) - len(set(norm))) / len(norm), 3)


def boilerplate_per_1k(text: str, *, n: int = 4, min_count: int = 5) -> float:
    body = "".join(CJK.findall(str(text or "")))
    if len(body) < n:
        return 0.0
    grams = Counter(body[i:i + n] for i in range(len(body) - n + 1))
    repeated = sum(c for c in grams.values() if c >= min_count)
    return round(repeated * 1000 / len(body), 1)


def term_candidates(corpus: str, *, top: int = 40, max_len: int = 4, min_count: int = 2) -> list[str]:
    """从资料原文里抽高频中文术语（2–4 字 n-gram，去掉停用词与碎片）。

    这是“考点/术语”的确定性代理：不保证语义完美，但可复现、可比较。
    """
    text = "".join(CJK.findall(str(corpus or "")))
    counter: Counter[str] = Counter()
    for run in CJK_RUN.findall(str(corpus or "")):
        for size in range(2, max_len + 1):
            for i in range(len(run) - size + 1):
                gram = run[i:i + size]
                if gram in STOP:
                    continue
                counter[gram] += 1
    scored: list[tuple[str, int]] = []
    for gram, count in counter.items():
        if count < min_count:
            continue
        # 更长的词优先，避免只留下“函数”“极限”这类碎片
        scored.append((gram, count * (1 + 0.3 * (len(gram) - 2))))
    scored.sort(key=lambda x: (-x[1], x[0]))
    picked: list[str] = []
    for gram, _score in scored:
        if any(gram in prev for prev in picked):
            continue
        picked.append(gram)
        if len(picked) >= top:
            break
    return picked


def term_recall(terms: list[str], text: str) -> dict:
    body = re.sub(r"\s+", "", str(text or ""))
    if not terms:
        return {"terms": 0, "hit": 0, "recall": 0.0, "missing": []}
    hit = [t for t in terms if t in body]
    missing = [t for t in terms if t not in body]
    return {"terms": len(terms), "hit": len(hit),
            "recall": round(len(hit) / len(terms), 3), "missing": missing[:20]}


def _tokens(text: str) -> set[str]:
    body = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", str(text or "")).lower()
    if len(body) < 2:
        return {body} if body else set()
    return {body[i:i + 2] for i in range(len(body) - 1)}


def citation_support(blocks: list[dict], page_text, *, threshold: float = 0.12) -> dict:
    """引用支持率：正文块引用的页，和这段话的内容是否有足够重合。

    page_text: 可调用对象，page_no -> 该页原文。
    """
    checked = 0
    supported = 0
    weak: list[str] = []
    for block in blocks:
        if block.get("kind") == "figure":
            continue
        text = str(block.get("text") or "").strip()
        refs = list(block.get("source_refs") or [])
        if not text or not refs:
            continue
        page_bits = []
        for ref in refs:
            try:
                start = int(ref["page_start"])
                end = int(ref.get("page_end") or start)
            except Exception:
                continue
            for p in range(start, end + 1):
                page_bits.append(str(page_text(p) or ""))
        if not page_bits:
            continue
        checked += 1
        bt = _tokens(text)
        pt = _tokens(" ".join(page_bits))
        if not bt or not pt:
            continue
        overlap = len(bt & pt) / max(1, len(bt))
        if overlap >= threshold:
            supported += 1
        else:
            weak.append(str(block.get("id") or ""))
    ratio = round(supported / checked, 3) if checked else 0.0
    return {"checked": checked, "supported": supported, "ratio": ratio, "weak_blocks": weak[:20]}


_NUM_PREFIX_RE = re.compile(
    r"^第\s*[一二三四五六七八九十百零\d]+\s*[章节篇]\s*"
    r"|^[一二三四五六七八九十]+\s*[、.]\s*"
    r"|^\d+(?:\.\d+){0,3}\s*")


def _norm_heading(text: str) -> str:
    body = re.sub(r"\s+", "", str(text or ""))
    body = _NUM_PREFIX_RE.sub("", body)
    return body.strip("：:·. ")


def heading_recall(headings: list[str], lecture_text: str) -> dict:
    """资料目录里的章节，讲义覆盖了多少（结构一致性，不依赖标注）。"""
    targets = [(_norm_heading(h), h) for h in headings or [] if _norm_heading(h)]
    if not targets:
        return {"headings": 0, "hit": 0, "recall": 0.0, "missing": []}
    body = re.sub(r"\s+", "", lecture_text or "")
    hit, missing = 0, []
    for norm, raw in targets:
        if norm and norm in body:
            hit += 1
        else:
            missing.append(raw)
    return {"headings": len(targets), "hit": hit,
            "recall": round(hit / len(targets), 3), "missing": missing[:20]}
