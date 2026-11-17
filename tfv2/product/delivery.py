
"""Delivery policy (Round 2).

Hard errors reject; soft problems must still be deliverable. Every artifact is
kept, exportable, and carries a machine-readable gap list so the UI can say
"partial: missing pages X, questions Y" instead of silently losing the work.
"""
from __future__ import annotations

from typing import Any

from tfv2.quality import trust

_HARD_MARKERS = (
    "总分", "题数", "分值合计", "近重复", "自纠错", "SymPy", "答案与解析",
    "没有可用", "蓝图", "不是 100", "缺参考答案", "选项", "页码",
)
_SOFT_MARKERS = ("页覆盖", "答案审计未完成", "选择题答案审计仍有", "图", "表格")


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(str(x) for x in items if str(x).strip()))


def _exam_gaps(doc: dict, audit: dict) -> dict:
    content = doc.get("content") or {}
    questions = [q for sec in content.get("sections") or [] for q in sec.get("questions") or []]
    pages = set((doc.get("coverage") or {}).get("pages") or [])
    cited = {int(q.get("source_page") or 0) for q in questions if q.get("source_page")}
    answer_audit = content.get("answer_audit") or {}
    return {
        "missing_pages": sorted(pages - cited),
        "question_count": len(questions),
        "audit_checked": bool(answer_audit.get("checked")),
        "audit_conflicts": len(answer_audit.get("conflicts") or []),
    }


def apply_exam_delivery(doc: dict) -> dict:
    audit = trust.audit_exam(doc)
    doc["trust"] = audit
    issues = _unique(list(doc.get("issues") or []) + list(audit.get("issues") or []))
    warnings = _unique(list(doc.get("warnings") or []) + list(audit.get("warnings") or []))
    gaps = _exam_gaps(doc, audit)
    hard: list[str] = []
    soft: list[str] = []
    for issue in issues:
        if "选择题答案审计仍有" in issue:
            if gaps["audit_conflicts"] >= 2:
                hard.append(issue)
            else:
                soft.append(issue)
        elif "页覆盖" in issue:
            soft.append(issue)
        elif any(marker in issue for marker in _HARD_MARKERS):
            hard.append(issue)
        else:
            # Unknown defects are treated as hard until proven soft.
            hard.append(issue)
    content = doc.get("content") or {}
    questions = [q for sec in content.get("sections") or [] for q in sec.get("questions") or []]
    if not questions:
        hard.append("没有任何可交付题目")
    user_blueprint = content.get("blueprint_source") == "user"
    only_coverage = bool(soft) and all("页覆盖" in x for x in soft)
    if hard:
        status = "rejected"
    elif soft:
        if only_coverage and user_blueprint:
            # 用户明确限定了题型/题量：这几道题落在 10 页还是 12 页不是他能改的缺陷。
            # 仍然把覆盖数写进 warnings，只是不因此把整卷降成 partial。
            status = "review" if (not gaps["audit_checked"]
                                  and any(q.get("qtype") == "choice" for q in questions)) else "validated"
        else:
            status = "partial" if any("页覆盖" in x for x in soft) else "review"
    elif not gaps["audit_checked"] and any(q.get("qtype") == "choice" for q in questions):
        status = "review"
    else:
        status = "validated"
    doc["status"] = status
    doc["issues"] = _unique(hard + soft)
    doc["warnings"] = warnings + [x for x in soft if x not in hard]
    doc["delivery"] = {
        "status": status,
        "hard_issues": hard,
        "soft_issues": soft,
        "warnings": warnings,
        "missing_pages": gaps["missing_pages"],
        "missing_questions": 0,
        "question_count": gaps["question_count"],
        "exportable": bool(questions),
        "retryable": bool(questions),
    }
    return doc


def apply_task_delivery(doc: dict) -> dict:
    kind = str(doc.get("kind") or "")
    if kind in ("paper", "analysis", "mindmap"):
        out = trust.apply_task_trust(dict(doc))
        out["delivery"] = {
            "status": out.get("status") or "rejected",
            "hard_issues": [] if out.get("status") != "rejected" else list(out.get("issues") or []),
            "soft_issues": [],
            "missing_pages": [],
            "missing_items": 0,
            "exportable": out.get("status") != "rejected",
            "retryable": True,
        }
        return out
    checked = trust.apply_task_trust(dict(doc))
    audit = checked.get("trust") or {}
    items = (doc.get("content") or {}).get("items") or []
    issues = _unique(list(checked.get("issues") or []))
    if kind == "extract_nouns":
        issues = [x for x in issues if "页覆盖" not in x]
    hard: list[str] = []
    soft: list[str] = []
    for issue in issues:
        if "页覆盖" in issue or "部分提取" in issue:
            soft.append(issue)
        else:
            hard.append(issue)
    if not items:
        hard.append("没有可交付条目")
    coverage = (doc.get("coverage") or {}).get("pages") or []
    cited = (doc.get("coverage") or {}).get("pages_cited") or []
    if hard:
        status = "rejected"
    elif soft:
        status = "partial"
    else:
        status = "validated"
    doc["status"] = status
    doc["issues"] = _unique(hard + soft)
    doc["delivery"] = {
        "status": status,
        "hard_issues": hard,
        "soft_issues": soft,
        "missing_pages": sorted(set(coverage) - set(cited)),
        "missing_items": 0,
        "exportable": bool(items),
        "retryable": bool(items),
    }
    return doc
