"""从 PageUnit 生成轻量整卷（选择题），供没有讲义的资料按页出题。

规则（确定性，不依赖模型）：
- 题量、每题分值、总分由这里算死，模型只负责出题；
- 页码必须落在用户选中的页里，模型给错页码就丢弃这道题，不能改写成别的页码；
- 选项必须 4 个互不相同、答案在下标 0–3 内；
- 题干重复、解析缺失、页码越界都记进 audit，状态随之降级；
- 选择题可自动判分；计算/简答类不在这里，避免冒充自动判对。
"""
from __future__ import annotations

import json
import re

from tfv2.domain.page_unit import build_page_unit
from tfv2.product.service import artifact_path

MAX_PAGES = 16
MAX_QUESTIONS = 20


def _norm_stem(text: str) -> str:
    return re.sub(r"[\s，。、；：？！,.;:?!]+", "", str(text or "")).lower()


def audit_unit_questions(items: list[dict], chosen: list[int], *, total: int = 100) -> dict:
    """逐题体检：返回 audit 明细，passed 决定这份卷能不能标 validated。"""
    problems: list[str] = []
    seen: set[str] = set()
    duplicates: list[int] = []
    bad_pages: list[int] = []
    for i, q in enumerate(items, start=1):
        stem = str(q.get("stem") or "").strip()
        if not stem:
            problems.append(f"第 {i} 题没有题干")
            continue
        key = _norm_stem(stem)
        if key in seen:
            duplicates.append(i)
            problems.append(f"第 {i} 题题干与前面重复")
        seen.add(key)
        opts = [str(x).strip() for x in (q.get("options") or [])]
        if len(opts) != 4 or len(set(opts)) != 4:
            problems.append(f"第 {i} 题选项不是 4 个互不相同的选项")
        ans = q.get("answer")
        if not isinstance(ans, int) or ans not in range(4):
            problems.append(f"第 {i} 题答案不在 0–3")
        page = int(q.get("page") or 0)
        if page not in chosen:
            bad_pages.append(i)
            problems.append(f"第 {i} 题页码 {page} 不在本次选定页内")
        if not str(q.get("explanation") or "").strip():
            problems.append(f"第 {i} 题缺少解析")
    return {
        "checked": True, "question_count": len(items),
        "score_each": round(total / len(items), 1) if items else 0.0,
        "duplicates": duplicates, "bad_pages": bad_pages, "problems": problems,
        "auto_gradable": True, "manual_types": [],
        "passed": not problems,
    }


def _split_scores(count: int, total: int = 100) -> list[float]:
    if count <= 0:
        return []
    base = round(total / count, 1)
    scores = [base] * count
    drift = round(total - sum(scores), 1)
    if abs(drift) >= 0.05:
        scores[-1] = round(scores[-1] + drift, 1)
    return scores


def _parse_questions(data: dict, chosen: list[int]) -> tuple[list[dict], list[dict]]:
    items: list[dict] = []
    dropped: list[dict] = []
    for raw_q in (data or {}).get("questions") or []:
        if not isinstance(raw_q, dict):
            dropped.append({"reason": "不是对象"})
            continue
        stem = str(raw_q.get("stem") or "").strip()
        opts = [str(x).strip() for x in (raw_q.get("options") or [])]
        try:
            ans = int(raw_q.get("answer"))
        except Exception:
            dropped.append({"reason": "答案不是整数", "stem": stem[:60]})
            continue
        if not stem or len(opts) != 4 or len(set(opts)) != 4 or ans not in range(4):
            dropped.append({"reason": "题干/选项/答案不合法", "stem": stem[:60]})
            continue
        try:
            page = int(raw_q.get("page") or 0)
        except Exception:
            page = 0
        if page not in chosen:
            # 页码不合法就丢弃：静默改成 chosen[0] 等于伪造出处。
            dropped.append({"reason": f"页码 {page} 不在选定页内", "stem": stem[:60]})
            continue
        items.append({"stem": stem, "options": opts, "answer": ans,
                      "explanation": str(raw_q.get("explanation") or "").strip(),
                      "page": page, "qtype": "choice"})
    return items, dropped


def exam_from_units(aid: str, pages: list[int], count: int = 5, subject: str = "",
                    client=None, total_score: int = 100) -> dict:
    path = artifact_path(aid)
    if path is None:
        raise ValueError("资料不存在")
    raw = json.loads((path / "source_pages.json").read_text(encoding="utf-8"))
    rows = raw.get("pages") or raw
    if not pages:
        raise ValueError("先选择资料页")
    bad = [p for p in pages if int(p) < 1 or int(p) > len(rows)]
    if bad:
        raise ValueError(f"页码超出资料范围：{sorted(set(bad))[:5]}")
    chosen = sorted({int(p) for p in pages})[:MAX_PAGES]
    parts, skipped = [], []
    for p in chosen:
        unit = build_page_unit(p, str(rows[p - 1].get("text") or ""))
        if unit.kind in ("text", "table") and unit.text.strip():
            parts.append(f"[第{p}页]\n{unit.text[:4000]}")
        else:
            skipped.append(p)
    if not parts:
        raise ValueError("这些页以公式/图片为主，暂不能直接出题；请选文字页")
    count = max(1, min(int(count), MAX_QUESTIONS))
    system = ("你是命题老师。只依据给定页码出单选题，每题 4 个不同选项、唯一正确答案、解析、页码。"
              "页码必须取自给定的页码，不要编造。"
              "只输出 JSON：{\"questions\":[{\"stem\":\"...\",\"options\":[\"A\",\"B\",\"C\",\"D\"],\"answer\":0,"
              "\"explanation\":\"...\",\"page\":1}]}。不要 Markdown。")
    user = f"科目：{subject}\n可用页码：{chosen}\n\n资料：\n" + "\n\n".join(parts) + f"\n\n请出 {count} 道题。"
    if client is None:
        try:
            from tfv2.llm.qwen_text import QwenTextClient
            client = QwenTextClient()
        except Exception:
            from tfv2.llm.client import DeepSeekClient
            client = DeepSeekClient(model="deepseek-flash")
    data = client.json(system, user, max_tokens=5000, temperature=0.2)
    items, dropped = _parse_questions(data, chosen)
    if not items:
        raise ValueError("模型没有返回合法题目（页码必须落在选定页内）")

    for q, s in zip(items, _split_scores(len(items), total_score)):
        q["score"] = s
    audit = audit_unit_questions(items, chosen, total=total_score)
    audit["dropped"] = dropped
    audit["skipped_pages"] = skipped
    issues = list(audit["problems"])
    if dropped:
        issues.append(f"丢弃了 {len(dropped)} 道不合法题目（页码/选项/答案不合法）")
    if skipped:
        issues.append(f"公式/图片页跳过：{skipped}")
    status = "validated" if audit["passed"] and not dropped else "review"

    used_pages = sorted({q["page"] for q in items})
    uncovered = sorted(set(chosen) - set(used_pages))
    section = {"name": "一、选择题", "type": "choice", "count": len(items),
               "score": round(sum(q["score"] for q in items), 1), "questions": items}
    return {
        "title": f"资料页出卷 {chosen[0]}–{chosen[-1]}", "subject": subject,
        "status": status, "issues": issues, "kind": "exam",
        "questions": items,
        "content": {
            "mode": "unit", "subject": subject, "sections": [section],
            "total_score": round(sum(q["score"] for q in items), 1),
            "answer_audit": audit,
            "coverage": {"pages": chosen, "pages_cited": used_pages, "uncovered_pages": uncovered},
            "grading": {"auto_kinds": ["choice"], "manual_kinds": [],
                        "note": "选择题自动判分；计算/简答题不在本卷，避免冒充自动判对"},
        },
        "skipped_pages": skipped,
        "dropped_questions": dropped,
    }
