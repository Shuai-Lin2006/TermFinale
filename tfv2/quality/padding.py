
"""Detects padding in generated lectures.

Word-count quotas invite the model to repeat itself or invent empty examples.
This module checks information gain instead: duplicate paragraphs, generic
transition sentences, examples with no concrete content, and repeated
sentences. It reports issues; it never rewrites content.
"""
from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher

_GENERIC = (
    "本节介绍了", "本小节介绍了", "综上所述", "总之", "值得注意的是",
    "首先，我们", "接下来，我们", "最后，我们", "通过本节",
    "本节学习了", "本小节学习了", "希望大家", "总而言之",
)
_WS = re.compile(r"\s+")
_SENT = re.compile(r"(?<=[。！？.!?；;])\s*")


def _norm(text: str) -> str:
    return _WS.sub("", text or "").lower()


def _block_dicts(section) -> list[dict]:
    if isinstance(section, dict):
        return [b for b in (section.get("blocks") or []) if isinstance(b, dict)]
    out = []
    for b in getattr(section, "blocks", []) or []:
        try:
            out.append(b.model_dump(mode="json"))
        except Exception:
            continue
    return out


def audit_section(section) -> list[str]:
    issues: list[str] = []
    blocks = _block_dicts(section)
    paragraphs = [str(b.get("text") or "").strip() for b in blocks if b.get("kind") == "paragraph"]
    examples = [str(b.get("text") or "").strip() for b in blocks if b.get("kind") == "example"]
    # 1. empty/generic paragraphs
    for text in paragraphs:
        if not text:
            continue
        if len(text) < 100 and any(p in text for p in _GENERIC):
            issues.append("空泛过渡段：" + text[:40])
    # 2. examples that contain no concrete material
    for text in examples:
        if not text:
            issues.append("空例题")
            continue
        if len(text) < 24:
            issues.append("例题过短，无拆解：" + text[:40])
            continue
        if not re.search(r"\d|\$|=|步骤|解[:：]|计算|证明|例", text):
            issues.append("例题没有具体条件/步骤：" + text[:40])
    # 3. repeated blocks within a section
    normed = [_norm(t) for t in paragraphs + examples if t]
    for i in range(len(normed)):
        for j in range(i + 1, len(normed)):
            if normed[i] and normed[i] == normed[j]:
                issues.append("重复段落/例题")
                break
            if normed[i] and normed[j] and SequenceMatcher(None, normed[i], normed[j]).ratio() >= 0.93:
                issues.append("近似重复段落/例题")
                break
    # 4. sentence-level repetition
    sentences = []
    for text in paragraphs + examples:
        sentences.extend(s.strip() for s in _SENT.split(text) if len(_norm(s)) >= 12)
    if len(sentences) >= 6:
        counts = Counter(_norm(s) for s in sentences)
        repeated = sum(n - 1 for n in counts.values() if n > 1)
        if repeated / len(sentences) > 0.2:
            issues.append(f"句子重复率 {repeated / len(sentences):.0%}")
    return list(dict.fromkeys(issues))


def audit_lecture(sections) -> dict:
    rows = []
    all_issues: list[str] = []
    for section in sections:
        title = section.get("title") if isinstance(section, dict) else getattr(section, "title", "")
        issues = audit_section(section)
        if issues:
            rows.append({"section": str(title or ""), "issues": issues})
            all_issues.extend(f"{title}: {x}" for x in issues)
    total = len(sections)
    return {
        "passed": not all_issues,
        "sections": total,
        "sections_with_issues": len(rows),
        "issues": all_issues,
        "rows": rows,
    }
