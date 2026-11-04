"""讲义去重：同一章被分块生成时，容易出现「完整版 +（续）版」重复。"""
from __future__ import annotations

import re
from difflib import SequenceMatcher


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def dedupe_markdown(md: str, threshold: float = 0.94) -> str:
    blocks = [b for b in re.split(r"\n{2,}", (md or "").strip()) if b.strip()]
    kept: list[str] = []
    seen_exact: set[str] = set()
    headings: set[str] = set()

    for block in blocks:
        norm = _norm(block)
        if not norm:
            continue
        if block.lstrip().startswith("#"):
            title = _norm(re.sub(r"^#+\s*", "", block))
            if block.lstrip().startswith("## "):
                headings.clear()  # 新的一章，允许小节标题重复
            if title in headings:
                continue
            headings.add(title)
            if "（续）" in title and len(title) <= 32:
                continue
            kept.append(block)
            continue
        if norm in seen_exact:
            continue
        if len(norm) > 60:
            duplicate = False
            for prev in kept[-20:]:
                pnorm = _norm(prev)
                if not pnorm or abs(len(pnorm) - len(norm)) > len(norm) * 0.35:
                    continue
                if SequenceMatcher(None, pnorm, norm).ratio() >= threshold:
                    duplicate = True
                    break
            if duplicate:
                continue
        seen_exact.add(norm)
        kept.append(block)
    text = "\n\n".join(kept)

    # 章内小节去重：分块生成时，同一章的后半段常把前面的小节再写一遍
    chapters = re.split(r"(?m)^(?=## )", text)
    rebuilt = []
    for chapter in chapters:
        sections = re.split(r"(?m)^(?=### )", chapter)
        if len(sections) <= 1:
            rebuilt.append(chapter)
            continue
        seen: set[str] = set()
        out = [sections[0]]
        for sec in sections[1:]:
            title = _norm(sec.splitlines()[0].lstrip("#").strip())
            title = re.sub(r"^[0-9.]+", "", title)
            if title in seen:
                continue
            seen.add(title)
            out.append(sec)
        rebuilt.append("\n\n".join(out))
    return "\n\n".join(rebuilt)
