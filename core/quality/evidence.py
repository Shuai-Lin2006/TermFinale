"""逐句证据审计：生成物里的每个论点，是否能在它引用的资料页找到依据。

这是“有页码”之外的下一层：引用页码 ≠ 该页支持这句话。
当前用 2-gram 覆盖率做保守启发式，后续可替换为 NLI/quote 检索。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

PAGE_HEADER_RE = re.compile(r"》\s*第\s*(\d+)\s*页】")
CITE_RE = re.compile(r"(?:第\s*(\d+)\s*页|P\.?\s*(\d+))")
IMAGE_RE = re.compile(r"\[\[\[IMAGE:.*?\]\]\]", re.S)
MATH_RE = re.compile(r"\$\$.*?\$\$|\$[^$\n]*\$", re.S)
HEADING_RE = re.compile(r"(?m)^#{1,6}\s+")


def _norm(text: str) -> str:
    text = IMAGE_RE.sub("", text or "")
    text = MATH_RE.sub(" ", text)
    text = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text)
    return text


def _grams(text: str, n: int = 2) -> set[str]:
    t = _norm(text)
    return {t[i:i + n] for i in range(max(0, len(t) - n + 1))}


def _page_texts(pages: list[str]) -> dict[int, str]:
    out = {}
    for block in pages or []:
        m = PAGE_HEADER_RE.search(block or "")
        if m:
            out[int(m.group(1))] = block
    return out


@dataclass
class EvidenceItem:
    text: str
    pages: list[int]
    score: float
    supported: bool


@dataclass
class EvidenceReport:
    total: int = 0
    supported: int = 0
    unsupported: int = 0
    no_citation: int = 0
    rate: float = 0.0
    items: list[EvidenceItem] = field(default_factory=list)
    unsupported_samples: list[str] = field(default_factory=list)


def audit_evidence(markdown: str, pages: list[str], threshold: float = 0.30) -> EvidenceReport:
    page_map = _page_texts(pages)
    report = EvidenceReport()
    if not page_map:
        return report
    page_grams = {n: _grams(t) for n, t in page_map.items()}
    # 按空行切块；跳过标题/结语/纯图片行
    blocks = [b.strip() for b in re.split(r"\n\s*\n", markdown or "") if b.strip()]
    for block in blocks:
        if block.lstrip().startswith("#") or block.strip() in ("---", "***"):
            continue
        # 讲解/延伸是解释层，不是资料事实；由前面的原文引文负责可溯源
        if block.lstrip().startswith(("**讲解**", "**延伸**", "**易错**", "**说明**")):
            continue
        if len(_norm(block)) < 18:
            continue
        cites = []
        for m in CITE_RE.finditer(block):
            n = int(m.group(1) or m.group(2))
            if n in page_map and n not in cites:
                cites.append(n)
        if not cites:
            report.total += 1
            report.no_citation += 1
            report.items.append(EvidenceItem(block[:120], [], 0.0, False))
            if len(report.unsupported_samples) < 8:
                report.unsupported_samples.append("无页码：" + block[:80])
            continue
        cg = _grams(block)
        best = 0.0
        for n in cites:
            pg = page_grams.get(n) or set()
            if not cg or not pg:
                continue
            best = max(best, len(cg & pg) / len(cg))
        ok = best >= threshold
        report.total += 1
        report.supported += 1 if ok else 0
        report.unsupported += 0 if ok else 1
        report.items.append(EvidenceItem(block[:120], cites, round(best, 3), ok))
        if not ok and len(report.unsupported_samples) < 8:
            report.unsupported_samples.append(
                f"低依据 {best:.0%}（{cites}）：" + block[:80])
    report.rate = round(report.supported / report.total, 3) if report.total else 0.0
    return report


def repair_citations(markdown: str, pages: list[str], threshold: float = 0.35) -> tuple[str, int]:
    """给没有页码/页码不支持的段落在原文页里找依据；匹配不到就不动。

    只在 2-gram 覆盖足够时补（P.N），不是按段平均分配页码。
    """
    page_map = _page_texts(pages)
    if not page_map:
        return markdown or "", 0
    page_grams = {n: _grams(t) for n, t in page_map.items()}
    blocks = re.split(r"(\n\s*\n)", markdown or "")
    repaired = 0
    out = []
    for block in blocks:
        if not block or block.isspace() or block.strip() in ("---", "***"):
            out.append(block); continue
        if block.lstrip().startswith("#"):
            out.append(block); continue
        if len(_norm(block)) < 18:
            out.append(block); continue
        cites = [int(m.group(1) or m.group(2)) for m in CITE_RE.finditer(block)]
        clean = CITE_RE.sub("", block)
        cg = _grams(clean)
        if not cg:
            out.append(block); continue
        best_n, best = None, 0.0
        for n, pg in page_grams.items():
            if not pg:
                continue
            score = len(cg & pg) / len(cg)
            if score > best:
                best_n, best = n, score
        if best_n is None or best < threshold:
            out.append(block); continue
        if cites and best <= threshold and any(c in page_map for c in cites):
            # 已有引用不算，避免覆盖正确引用
            out.append(block); continue
        # 无引用，或引用页本身匹配很低 → 改为最佳真实页
        new_block = CITE_RE.sub("", block).rstrip()
        new_block = new_block + f"（P.{best_n}）"
        out.append(new_block)
        repaired += 1
    return "".join(out), repaired
