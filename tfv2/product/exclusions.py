
"""Structured user exclusions.

Users do not say "delete page 3". They say "积分中值定理不考", "计算题不考",
"老师说不考泰勒展开", "实验部分跳过". This module turns those into structured
specs, matches them against the material, and provides deterministic filters for
lecture / extraction / exam / practice. Ambiguous phrases are returned for
confirmation and never silently delete content.
"""
from __future__ import annotations

import re
from typing import Any

_NEG = ("不考", "不用考", "不要求", "不需要", "不用", "跳过", "略过", "不测",
        "不学", "不看", "免考", "别考", "不复习", "不作为考试", "不纳入考试")
_GENERIC = {"太多", "太难", "太难了", "所有", "全部", "这些", "那些", "这个", "那个",
            "该考点", "这个考点", "上述内容", "它", "这部分", "那部分"}
_QTYPES = {
    "选择": "choice", "选择题": "choice", "单选": "choice",
    "计算": "calculation", "计算题": "calculation",
    "简答": "short_answer", "简答题": "short_answer",
    "判断": "judgment", "判断题": "judgment",
    "填空": "fill_blank", "填空题": "fill_blank",
    "证明": "proof", "证明题": "proof",
    "论述": "essay", "论述题": "essay",
    "实验": "experiment", "实验题": "experiment",
}
_ALIASES = {
    "积分中值定理": ["中值定理", "积分中值"],
    "泰勒展开": ["泰勒公式", "Taylor展开", "taylor展开"],
    "交感神经": ["交感"],
    "副交感神经": ["副交感"],
    "牵涉性痛": ["牵涉痛"],
    "选择题": ["choice"], "计算题": ["calculation"],
    "简答题": ["short_answer"], "判断题": ["judgment"],
    "实验": ["experiment"],
}


_CN_NUM = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
           "七": 7, "八": 8, "九": 9, "十": 10}


def _norm(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("（）", "()").replace("，", ",").replace("：", ":")
    return re.sub(r"[\s\u3000，,。；;、:：!?！？\"'“”‘’()（）\[\]【】]+", "", text)


def _cn_to_int(value: str) -> int | None:
    value = value.strip()
    if value.isdigit():
        return int(value)
    if value == "十":
        return 10
    if value.startswith("十"):
        return 10 + _CN_NUM.get(value[1:], 0) if len(value) > 1 else 10
    if "十" in value:
        left, right = value.split("十", 1)
        return _CN_NUM.get(left, 0) * 10 + (_CN_NUM.get(right, 0) if right else 0)
    return _CN_NUM.get(value)


def _clean_topic(text: str) -> str:
    text = re.sub(r"^(?:了|的|吧|啊|呢)+", "", text.strip())
    text = re.sub(r"(?:了|吧|啊|呢|的)+$", "", text).strip()
    text = re.sub(r"^(?:考|学|看|复习|背|出)+", "", text).strip()
    return text[:80]


def _add(specs: list[dict], scope: str, value: str, *, applies: list[str] | None = None,
         confidence: float = 0.95, quote: str = "", terms: list[str] | None = None) -> None:
    value = value.strip()
    if not value:
        return
    key = (scope, _norm(value))
    if any((s["scope"], _norm(s["value"])) == key for s in specs):
        return
    expanded = list(terms or [])
    for canonical, aliases in _ALIASES.items():
        if value == canonical or value in aliases:
            expanded.extend([canonical, *aliases])
    expanded.extend(_ALIASES.get(value, []))
    specs.append({
        "scope": scope, "value": value,
        "normalized_terms": list(dict.fromkeys([_norm(value)] + [_norm(t) for t in expanded if t])),
        "applies_to": applies or ["lecture", "extract", "exam", "practice"],
        "confidence": confidence, "source_quote": quote,
    })


def parse_exclusions(text: str) -> dict:
    """Rule parser. Deterministic, offline, and testable.

    The LLM is not required: these patterns cover the phrases users actually
    type. Anything that cannot be scoped safely is returned as ambiguous.
    """
    raw = (text or "").strip()
    specs: list[dict] = []
    ambiguous: list[dict] = []
    ignored: list[str] = []
    if not raw:
        return {"specs": [], "ambiguous": [], "ignored": []}

    # split on sentence/clause boundaries; keep 和/与 inside topics
    clauses = [c.strip() for c in re.split(r"[\n\r,，;；。]+|(?:并且|以及|还有)", raw) if c.strip()]
    for clause in clauses:
        s = clause.strip()
        s = re.sub(r"^(?:我们|我)?(?:老师|导师|教授)(?:说|讲|强调|要求|提到)?\s*", "", s)
        s = re.sub(r"^(?:请|帮我|帮忙|麻烦)\s*", "", s)
        if not s:
            continue
        # "只考到第5章" / "范围到第5章"
        m = re.search(r"(?:只考到|仅考到|考到|范围到|只到)\s*第?\s*([0-9一二三四五六七八九十]+)\s*章", s)
        if m and _cn_to_int(m.group(1)) is not None:
            _add(specs, "section_limit", str(_cn_to_int(m.group(1))), applies=["lecture", "extract", "exam", "practice"],
                 confidence=0.9, quote=clause)
            continue
        m_except = re.search(r"^除了\s*(.+?)\s*(?:都考|全考|其余都考|其他都考)", s)
        if m_except:
            topic = _clean_topic(m_except.group(1))
            if len(_norm(topic)) >= 2:
                _add(specs, "topic", topic, confidence=0.9, quote=clause)
            else:
                ambiguous.append({"quote": clause[:120], "candidate": topic,
                                  "reason": "除了后面的考点不明确"})
            continue
        if not any(neg in s for neg in _NEG) and not re.search(r"(只考|仅考|只出|只测)", s):
            ignored.append(clause[:120])
            continue
        # page
        pages = re.findall(r"第?\s*(\d+)\s*页", s)
        if pages:
            for p in pages:
                _add(specs, "page", str(int(p)), confidence=0.98, quote=clause)
            continue
        # section / chapter
        sections = re.findall(r"第\s*([0-9一二三四五六七八九十]+)\s*([章节])", s)
        if sections:
            for num, unit in sections:
                n = _cn_to_int(num)
                if n is None:
                    continue
                _add(specs, "section", f"第{n}{unit}", confidence=0.96, quote=clause)
            continue
        # question type: allow-list
        allow = re.search(r"(?:只考|仅考|只出|只测)\s*(选择|单选|计算|简答|判断|填空|证明|论述|实验)题?", s)
        if allow:
            qtype = _QTYPES.get(allow.group(1))
            if qtype:
                _add(specs, "question_type_allow", qtype, applies=["exam", "practice"],
                     confidence=0.95, quote=clause)
                continue
        # question type: deny-list
        hit_q = None
        for token, qtype in sorted(_QTYPES.items(), key=lambda x: -len(x[0])):
            if token not in s:
                continue
            immediate = re.search(re.escape(token) + r"题?\s*(?:" + "|".join(map(re.escape, _NEG)) + r")", s)
            if token.endswith("题") or immediate:
                hit_q = qtype
                break
        if hit_q:
            _add(specs, "question_type", hit_q, applies=["exam", "practice"],
                 confidence=0.95, quote=clause)
            continue
        # topic: prefix negative ("不考 X", "别考 X")
        m = re.search(r"^(?:不考|不用考|不要求|不需要|不用|跳过|略过|不测|不学|不看|免考|别考)\s*[:：]?\s*(.+)$", s)
        topic = _clean_topic(m.group(1)) if m else ""
        # topic: suffix negative ("X 不考")
        if not topic:
            m = re.search(r"^(.+?)\s*(?:不考|不用考|不要求|不需要|跳过|略过|不测|不学|不看|免考|别考)\s*$", s)
            topic = _clean_topic(m.group(1)) if m else ""
        # "除了 X 都考"
        if not topic:
            m = re.search(r"^除了\s*(.+?)\s*(?:都考|全考|其余都考)", s)
            topic = _clean_topic(m.group(1)) if m else ""
        if topic:
            nt = _norm(topic)
            if len(nt) < 2 or nt in {_norm(x) for x in _GENERIC} or re.search(r"(这个|那个|该|上述|它)", topic):
                ambiguous.append({"quote": clause[:120], "candidate": topic,
                                  "reason": "没有说明具体是哪个考点/哪一页/哪一章"})
                continue
            # "实验部分" -> topic 实验
            topic = re.sub(r"(?:部分|内容|章节|这一块|这块)$", "", topic).strip() or topic
            _add(specs, "topic", topic, confidence=0.9, quote=clause)
            continue
        ambiguous.append({"quote": clause[:120], "candidate": s[:80],
                          "reason": "能看出是不考，但没定位到页/章/考点/题型"})

    return {"specs": specs, "ambiguous": ambiguous, "ignored": ignored}


def specs_from_requirements(requirements: dict | None, excluded: str = "", custom_prompt: str = "") -> dict:
    labels = []
    for item in (requirements or {}).get("must_not") or []:
        if isinstance(item, dict):
            label = str(item.get("label") or "").strip()
            if label:
                labels.append(label)
            for alias in item.get("aliases") or []:
                if str(alias).strip():
                    labels.append(str(alias).strip())
        elif str(item).strip():
            labels.append(str(item).strip())
    text = "\n".join([excluded or "", custom_prompt or "", *labels])
    return parse_exclusions(text)


def build_index(page_text: dict[int, str], sections: list[dict] | None = None) -> dict:
    sections = sections or []
    return {
        "pages": {int(p): str(t or "") for p, t in page_text.items()},
        "sections": [
            {"id": str(s.get("id") or ""), "title": str(s.get("title") or ""),
             "pages": [int(p) for p in s.get("pages") or []],
             "text": str(s.get("text") or "")}
            for s in sections
        ],
    }


def _section_numbers(title: str) -> list[int]:
    out = []
    for m in re.finditer(r"第\s*([0-9一二三四五六七八九十]+)\s*[章节]", title or ""):
        n = _cn_to_int(m.group(1))
        if n is not None:
            out.append(n)
    return out


def match_specs(specs: list[dict], index: dict) -> list[dict]:
    pages = index.get("pages") or {}
    sections = index.get("sections") or []
    out = []
    for spec in specs:
        s = dict(spec)
        matched_pages: set[int] = set()
        matched_sections: list[str] = []
        terms = [t for t in (s.get("normalized_terms") or [_norm(s.get("value", ""))]) if t]
        scope = s.get("scope")
        if scope == "page":
            try:
                matched_pages.add(int(s["value"]))
            except Exception:
                pass
        elif scope in ("section", "section_limit"):
            if scope == "section_limit":
                limit = int(s["value"])
                for sec in sections:
                    nums = _section_numbers(sec.get("title", ""))
                    if nums and max(nums) > limit:
                        matched_sections.append(sec.get("id") or sec.get("title", ""))
                        matched_pages.update(sec.get("pages") or [])
                if not matched_sections:
                    for p, text in pages.items():
                        nums = _section_numbers(text[:80])
                        if nums and max(nums) > limit:
                            matched_pages.add(p)
            else:
                target = _norm(s["value"]).replace("章节", "章")
                target_nums = set(_section_numbers(s["value"]))
                for sec in sections:
                    title = _norm(sec.get("title", ""))
                    nums = set(_section_numbers(sec.get("title", "")))
                    if (target_nums and target_nums & nums) or (target and target in title):
                        matched_sections.append(sec.get("id") or sec.get("title", ""))
                        matched_pages.update(sec.get("pages") or [])
                if not matched_sections:
                    for p, text in pages.items():
                        if target_nums:
                            if target_nums & set(_section_numbers(text[:80])):
                                matched_pages.add(p)
                        elif target and target in _norm(text[:200]):
                            matched_pages.add(p)
        elif scope == "topic":
            for p, text in pages.items():
                nt = _norm(text)
                if any(t and t in nt for t in terms):
                    matched_pages.add(p)
            for sec in sections:
                title = _norm(sec.get("title", ""))
                if any(t and t in title for t in terms):
                    matched_sections.append(sec.get("id") or sec.get("title", ""))
        # question types do not map to pages
        total = max(1, len(pages))
        ratio = round(len(matched_pages) / total, 4) if total else 0.0
        needs_confirm = bool(
            s.get("confidence", 1.0) < 0.9
            or (scope in ("topic",) and ratio > 0.3 and len(pages) >= 4)
        )
        s["matched"] = {
            "pages": sorted(matched_pages),
            "sections": sorted(set(matched_sections)),
            "ratio": ratio,
        }
        s["needs_confirm"] = needs_confirm
        out.append(s)
    return out


def exclusion_prompt(specs: list[dict], applies: str = "lecture") -> str:
    specs = [s for s in specs if applies in (s.get("applies_to") or [])]
    if not specs:
        return ""
    parts = []
    for s in specs:
        scope = s.get("scope")
        value = s.get("value")
        if scope == "page":
            parts.append(f"第 {value} 页")
        elif scope == "section":
            parts.append(str(value))
        elif scope == "section_limit":
            parts.append(f"第 {value} 章之后的内容")
        elif scope == "question_type":
            label = next((k for k, v in _QTYPES.items() if v == value and len(k) >= 2), value)
            parts.append(f"{label}题")
        elif scope == "question_type_allow":
            label = next((k for k, v in _QTYPES.items() if v == value and len(k) >= 2), value)
            parts.append(f"除{label}题以外的题型")
        elif scope == "topic":
            parts.append(str(value))
    if not parts:
        return ""
    joined = "；".join(dict.fromkeys(parts))
    if applies == "lecture":
        return ("用户把以下内容标记为不考/不复习：" + joined +
                "。讲义不要主动展开；如果某页只是顺带提到，保留该页其他内容，不要整页删；"
                "只有整节/整页主要讲它时才跳过。用户说“不考”不等于“不能理解”，不要把同页相关内容一起删。")
    if applies == "extract":
        return ("提取结果不要包含用户标记为不考的内容：" + joined +
                "。如果一条条目同时包含不考内容和必考内容，保留必考部分，不要整条丢弃。")
    return ("出题/练习不要考用户标记为不考的内容：" + joined +
            "。不要用同义改写绕过；但同一情境里可以考相邻的必考知识点。")


def _term_hit(text: str, specs: list[dict], applies: str) -> bool:
    nt = _norm(text)
    if not nt:
        return False
    for s in specs:
        if applies not in (s.get("applies_to") or []):
            continue
        if s.get("scope") not in ("topic", "section", "section_limit"):
            continue
        for t in s.get("normalized_terms") or []:
            if t and t in nt:
                return True
    return False


def preview_exclusions(text: str, page_text: dict[int, str], sections: list[dict] | None = None) -> dict:
    """Backend preview for the confirmation UI: what would be removed."""
    parsed = parse_exclusions(text)
    matched = match_specs(parsed["specs"], build_index(page_text, sections or []))
    active = [s for s in matched if not s.get("needs_confirm")]
    pending = [s for s in matched if s.get("needs_confirm")]
    return {
        "specs": matched,
        "active": active,
        "pending_confirmation": pending,
        "ambiguous": parsed["ambiguous"],
        "requires_confirmation": bool(pending or parsed["ambiguous"]),
        "preview": {
            "pages": sorted({p for s in active for p in (s.get("matched") or {}).get("pages") or []}),
            "sections": sorted({sec for s in active for sec in (s.get("matched") or {}).get("sections") or []}),
        },
    }


def text_hit(text: str, specs: list[dict], applies: str = "extract") -> bool:
    return _term_hit(text, specs, applies)


def section_exceeds_limit(title: str, limit: int) -> bool:
    nums = _section_numbers(title)
    return bool(nums and max(nums) > int(limit))


def filter_blocks(blocks: list[Any], specs: list[dict], excluded_pages: set[int] | None = None) -> tuple[list[Any], int]:
    excluded_pages = excluded_pages or set()
    kept = []
    removed = 0
    for block in blocks:
        text = str(getattr(block, "text", "") or "")
        refs = getattr(block, "source_refs", []) or []
        ref_pages = set()
        for ref in refs:
            try:
                ref_pages.update(range(int(ref.page_start), int(getattr(ref, "page_end", None) or ref.page_start) + 1))
            except Exception:
                pass
        fig = getattr(block, "figure", None)
        caption = str(getattr(fig, "caption", "") or "") if fig is not None else ""
        if _term_hit(caption, specs, "lecture"):
            removed += 1
            continue
        if _term_hit(text, specs, "lecture"):
            nt = _norm(text)
            hits = sum(nt.count(t) for s in specs for t in (s.get("normalized_terms") or []))
            # A long paragraph that merely mentions an excluded term once is not
            # "the paragraph is about it"; keep it and let the lecture prompt
            # avoid expanding it. Short/central paragraphs are removed.
            if len(nt) < 120 or hits >= 2:
                removed += 1
                continue
        if ref_pages and ref_pages.issubset(excluded_pages):
            removed += 1
            continue
        kept.append(block)
    return kept, removed


def filter_items(items: list[dict], specs: list[dict], kind: str) -> tuple[list[dict], int]:
    kept = []
    removed = 0
    for item in items:
        if kind == "extract_points":
            text = f"{item.get('point', '')} {item.get('detail', '')}"
        elif kind == "extract_nouns":
            text = f"{item.get('term', '')} {item.get('definition', '')}"
        else:
            text = f"{item.get('stem', '')} {' '.join(map(str, item.get('options') or []))} {item.get('analysis', '')}"
        if _term_hit(text, specs, "extract"):
            removed += 1
            continue
        kept.append(item)
    return kept, removed


def question_excluded(q: dict, specs: list[dict]) -> bool:
    text = f"{q.get('stem', '')} {' '.join(map(str, q.get('options') or []))} {q.get('analysis', '')}"
    return _term_hit(text, specs, "exam") or _term_hit(text, specs, "practice")


def filter_questions(questions: list[dict], specs: list[dict], applies: str = "exam") -> tuple[list[dict], int]:
    kept = []
    removed = 0
    for q in questions:
        text = f"{q.get('stem', '')} {' '.join(map(str, q.get('options') or []))} {q.get('analysis', '')}"
        if _term_hit(text, specs, applies):
            removed += 1
            continue
        kept.append(q)
    return kept, removed


def report(specs: list[dict], *, ambiguous: list[dict] | None = None,
           removed_blocks: int = 0, removed_items: int = 0, removed_questions: int = 0) -> dict:
    return {
        "specs": specs,
        "ambiguous": ambiguous or [],
        "stats": {
            "excluded_pages": sorted({p for s in specs for p in (s.get("matched") or {}).get("pages") or []}),
            "removed_blocks": removed_blocks,
            "removed_items": removed_items,
            "removed_questions": removed_questions,
        },
    }
