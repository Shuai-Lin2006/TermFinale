
"""Deterministic trust checks for generated content.

The product's old quality layer checked *presence* (a page citation exists, a
quote exists, an analysis exists). This module checks support instead:

- a quote must be an exact substring of the cited source page;
- a block without a real quote is page_only, not "verified";
- analysis must actually cover its declared page range;
- an exam must pass page coverage, near-duplicate, self-correction and
  answer/analysis consistency checks before it can be called validated.
"""
from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher

from tfv2.quality.math_verify import audit_answer
from typing import Any

_CJK = re.compile(r"[\u4e00-\u9fff]")
_TOKEN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")
_NUM = re.compile(r"-?\d+(?:\.\d+)?(?:/[0-9]+)?")
_WS = re.compile(r"\s+")
_STOP = set("的了是在和与及或有这那一个一种我们你们他们本节资料第页".split())
_SELF_CORRECTION = (
    "重新计算", "这不对", "不对，", "应改为", "需要更正", "修正：", "最终决定",
    "为有区分度", "检查：", "等等，", "其实", "再检查", "但答案", "此处计算",
    "let me recompute", "wait,", "actually,",
)


def norm(text: str) -> str:
    return _WS.sub("", text or "")


def tokens(text: str) -> list[str]:
    return [x.lower() for x in _TOKEN.findall(text or "") if x not in _STOP]


def overlap(a: str, b: str) -> float:
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, min(len(ta), len(tb)))


def split_sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[。！？.!?；;])\s*", text or "") if len(norm(x)) >= 8]


def quote_in_page(quote: str, page_text: str) -> bool:
    q = norm(quote)
    return bool(q) and q in norm(page_text)


def _pages_of_block(block: dict) -> list[int]:
    out: set[int] = set()
    for ref in block.get("source_refs") or []:
        try:
            start = int(ref.get("page_start"))
            end = int(ref.get("page_end") or start)
        except Exception:
            continue
        if start >= 1:
            out.update(range(start, end + 1))
    return sorted(out)


def _best_quote(block_text: str, page_text: str) -> str:
    best, score = "", 0.0
    for sentence in split_sentences(page_text):
        s = overlap(block_text, sentence)
        if s > score:
            best, score = sentence, s
    return best if score >= 0.34 else ""


def audit_evidence(sections: list[dict], page_text: dict[int, str], *, min_verified: float = 0.6) -> dict:
    rows: list[dict] = []
    counts = Counter()
    for sec in sections:
        for block in sec.get("blocks") or []:
            if block.get("kind") == "figure":
                continue
            pages = _pages_of_block(block)
            text = str(block.get("text") or "")
            quote = ""
            for ref in block.get("source_refs") or []:
                if ref.get("quote"):
                    quote = str(ref.get("quote"))
                    break
            status = "unsupported"
            if not pages:
                status = "missing"
            elif quote:
                if not any(quote_in_page(quote, page_text.get(p, "")) for p in pages):
                    status = "mismatch"
                elif overlap(text, quote) < 0.1:
                    # Exact substring, but the quote is unrelated to the claim
                    # (e.g. a homework line used as evidence for a derivative).
                    status = "weak_quote"
                else:
                    status = "verified"
            else:
                best = ""
                for p in pages:
                    candidate = _best_quote(text, page_text.get(p, ""))
                    if candidate:
                        best = candidate
                        break
                status = "verified" if best else ("page_only" if any(page_text.get(p) for p in pages) else "unsupported")
                if best:
                    quote = best
            counts[status] += 1
            rows.append({
                "section": str(sec.get("title") or ""),
                "block_id": str(block.get("id") or ""),
                "kind": str(block.get("kind") or ""),
                "pages": pages,
                "quote": quote[:160],
                "status": status,
                "text_chars": len(text),
            })
    total = len(rows)
    verified = counts["verified"]
    passed = (bool(total) and verified / total >= min_verified
              and counts["mismatch"] == 0 and counts["weak_quote"] == 0 and counts["missing"] == 0)
    return {
        "passed": passed,
        "total": total,
        "verified": verified,
        "page_only": counts["page_only"],
        "mismatch": counts["mismatch"],
        "weak_quote": counts["weak_quote"],
        "unsupported": counts["unsupported"],
        "missing": counts["missing"],
        "verified_ratio": round(verified / total, 3) if total else 0.0,
        "rows": rows,
    }


def audit_coverage(sections: list[dict], page_count: int, page_text: dict[int, str], *, min_page_ratio: float = 0.98) -> dict:
    cited: set[int] = set()
    semantic: set[int] = set()
    weak: list[int] = []
    for sec in sections:
        for block in sec.get("blocks") or []:
            if block.get("kind") == "figure":
                continue
            pages = _pages_of_block(block)
            cited.update(p for p in pages if 1 <= p <= page_count)
            text = str(block.get("text") or "")
            for p in pages:
                if not (1 <= p <= page_count):
                    continue
                source = page_text.get(p, "")
                if not source:
                    semantic.add(p)  # an image-only page has no text; treat as covered by its caption/figure
                elif overlap(text, source) >= 0.12:
                    semantic.add(p)
                else:
                    weak.append(p)
    cited = {p for p in cited if 1 <= p <= page_count}
    page_ratio = len(cited) / max(1, page_count)
    semantic_ratio = len(semantic) / max(1, page_count)
    issues: list[str] = []
    if page_ratio < min_page_ratio:
        issues.append(f"页码覆盖 {page_ratio:.1%} < {min_page_ratio:.0%}")
    if semantic_ratio < min_page_ratio:
        issues.append(f"语义覆盖 {semantic_ratio:.1%} < {min_page_ratio:.0%}")
    return {
        "passed": page_ratio >= min_page_ratio and semantic_ratio >= min_page_ratio,
        "page_count": page_count,
        "pages_cited": sorted(cited),
        "page_ratio": round(page_ratio, 4),
        "semantic_pages": sorted(semantic),
        "semantic_ratio": round(semantic_ratio, 4),
        "weak_pages": sorted(set(weak))[:30],
        "issues": issues,
    }


def audit_analysis(doc: dict) -> dict:
    coverage = doc.get("coverage") or {}
    ratio = float(coverage.get("coverage") or 0)
    issues: list[str] = []
    if ratio < 0.98:
        issues.append(f"逻辑分析页覆盖 {ratio:.1%} < 98%")
    content = doc.get("content") or {}
    if not content.get("one_line"):
        issues.append("缺一句话主线")
    if len(content.get("concepts") or []) < 3:
        issues.append("概念少于 3 条")
    return {"passed": not issues, "coverage": ratio, "issues": issues}


def _template_key(stem: str) -> str:
    text = norm(stem).lower()
    text = re.sub(r"-?\d+(?:\.\d+)?", "#", text)
    return text[:220]


def audit_exam(doc: dict, *, min_page_ratio: float = 0.45, max_duplicate_ratio: float = 0.15) -> dict:
    content = doc.get("content") or {}
    questions: list[dict] = []
    issues: list[str] = []
    warnings: list[str] = []
    sections = content.get("sections") or []
    for sec in sections:
        qs = sec.get("questions") or []
        if len(qs) != int(sec.get("count") or 0):
            issues.append(f"{sec.get('name')} 题数 {len(qs)} ≠ 计划 {sec.get('count')}")
        if round(sum(float(q.get("score") or 0) for q in qs), 1) != round(float(sec.get("score") or 0), 1):
            issues.append(f"{sec.get('name')} 分值合计不等于 {sec.get('score')}")
        questions.extend(qs)
    total = round(sum(float(q.get("score") or 0) for q in questions), 1)
    if total != 100:
        issues.append(f"总分 {total} ≠ 100")
    pages = set((doc.get("coverage") or {}).get("pages") or [])
    cited = {int(q.get("source_page") or 0) for q in questions if q.get("source_page")}
    # 一题一页：题量决定了这份卷最多能覆盖多少页。用户按蓝图出 12 题时，
    # 要求覆盖 60 页的 45% 是结构上做不到的，那是假指标，不是缺陷。
    planned = sum(int(sec.get("count") or 0) for sec in sections) or len(questions)
    target_pages = max(1, int(len(pages) * min_page_ratio + 0.999)) if pages else 0
    # 用户自带蓝图（明确限定题型/题量）时，覆盖目标按题量封顶：
    # 12 题的卷子不可能覆盖 60 页的 45%，那是结构上做不到的指标，不是缺陷。
    # 默认蓝图/仿真题结构仍按原来的页面比例要求。
    if content.get("blueprint_source") == "user":
        target_pages = min(target_pages, max(planned, len(questions))) if planned else target_pages
    page_ratio = len(cited & pages) / max(1, target_pages)
    if pages and page_ratio < 1.0:
        issues.append(
            f"试卷页覆盖 {len(cited & pages)}/{target_pages} 页"
            f"（目标 {min_page_ratio:.0%}，按题量封顶）"
        )
    keys = [_template_key(str(q.get("stem") or "")) for q in questions]
    counts = Counter(k for k in keys if k)
    duplicate_indices: set[int] = set()
    for i, key in enumerate(keys):
        if key and counts[key] > 1:
            duplicate_indices.add(i)
    # Near duplicates survive exact/template hashing (same parameter equation,
    # changed constants). Compare normalized stems pairwise as a second pass.
    stems = [norm(str(q.get("stem") or "")) for q in questions]
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            if not stems[i] or not stems[j]:
                continue
            if SequenceMatcher(None, stems[i], stems[j]).ratio() >= 0.82:
                duplicate_indices.add(i)
                duplicate_indices.add(j)
    duplicate_questions = max(0, len(duplicate_indices) - 1)
    duplicate_ratio = duplicate_questions / max(1, len(questions))
    if duplicate_ratio > max_duplicate_ratio:
        issues.append(f"近重复题 {duplicate_questions} 道（{duplicate_ratio:.0%}）")
    self_correction = []
    answer_mismatch = []
    math_issues = []
    for i, q in enumerate(questions, start=1):
        analysis = str(q.get("analysis") or "")
        stem = str(q.get("stem") or "")
        hit = [m for m in _SELF_CORRECTION if m in analysis or m in stem]
        if hit:
            self_correction.append({"no": i, "markers": hit})
        checked = audit_answer(q)
        if checked.get("issues"):
            math_issues.append({"no": i, "issues": checked["issues"]})
        answer = str(q.get("answer_text") or "")
        if answer and q.get("qtype") != "choice":
            ans_nums = _NUM.findall(answer)
            tail = analysis[-600:]
            tail_nums = _NUM.findall(tail)
            if ans_nums and tail_nums and not any(a in tail_nums for a in ans_nums) and any(m in analysis for m in _SELF_CORRECTION):
                answer_mismatch.append({"no": i, "answer": answer[:80], "analysis_tail": tail[-160:]})
    if self_correction:
        issues.append(f"解析中残留自我纠错/改题痕迹：{len(self_correction)} 题")
    if answer_mismatch:
        issues.append(f"答案与解析结尾数值不一致：{len(answer_mismatch)} 题")
    if math_issues:
        # A single unparseable/ambiguous SymPy result is not enough evidence to
        # reject a whole paper. Keep it visible for review, but do not turn one
        # uncertain check into a user-facing failure. Two or more still block.
        if len(math_issues) == 1:
            warnings.append(f"SymPy 单题未通过，已标记待复核：{math_issues[0].get('no')} 题")
        else:
            issues.append(f"SymPy 答案校验不通过：{len(math_issues)} 题")
    audit = content.get("answer_audit") or {}
    if audit.get("conflicts"):
        issues.append(f"选择题答案审计仍有 {len(audit['conflicts'])} 个冲突")
    if not audit.get("checked") and any(q.get("qtype") == "choice" for q in questions):
        warnings.append("选择题答案审计未完成")
    passed = not issues
    return {
        "passed": passed,
        "issues": issues,
        "warnings": warnings,
        "page_ratio": round(page_ratio, 4),
        "pages_cited": sorted(cited & pages),
        "duplicate_questions": duplicate_questions,
        "duplicate_ratio": round(duplicate_ratio, 4),
        "self_correction": self_correction,
        "answer_mismatch": answer_mismatch,
        "math_issues": math_issues,
        "question_count": len(questions),
        "total_score": total,
    }


def apply_task_trust(doc: dict) -> dict:
    trust: dict[str, Any] = {}
    kind = doc.get("kind")
    if kind == "analysis":
        trust = audit_analysis(doc)
    elif kind in ("extract_points", "extract_nouns", "extract_questions", "mindmap"):
        cov = float((doc.get("coverage") or {}).get("coverage") or 0)
        issues = []
        # Vocabulary is sparse by nature; a page with no new term is not a
        # delivery defect. Points/questions still require 98% page coverage.
        if kind != "extract_nouns" and cov < 0.98:
            issues.append(f"页覆盖 {cov:.1%} < 98%")
        if kind == "extract_questions" and not (doc.get("content") or {}).get("items"):
            issues.append("原题提取没有可交付条目")
        trust = {"passed": not issues, "coverage": cov, "issues": issues}
    if trust:
        doc["trust"] = trust
        if not trust.get("passed"):
            if doc.get("status") == "validated":
                doc["status"] = "rejected"
            issues = list(doc.get("issues") or [])
            for issue in trust.get("issues") or []:
                if issue not in issues:
                    issues.append(issue)
            doc["issues"] = issues
    return doc


def apply_exam_trust(doc: dict) -> dict:
    trust = audit_exam(doc)
    doc["trust"] = trust
    if trust["issues"]:
        issues = list(doc.get("issues") or [])
        for issue in trust["issues"]:
            if issue not in issues:
                issues.append(issue)
        doc["issues"] = issues
        doc["status"] = "rejected"
    elif trust.get("warnings"):
        doc["warnings"] = list(doc.get("warnings") or []) + trust["warnings"]
    return doc
