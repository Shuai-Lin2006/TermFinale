"""教学单元规划：把页账本变成有讲解顺序的章节，而不是按页硬切。

LLM 只提出“单元标题 + 连续页码”；这里做严格的覆盖校验。任何不连续、
漏页、重页、顺序倒置或数量失控的方案都回退到原来的大纲/页切方案。
"""
from __future__ import annotations

import json
import re
from typing import Iterable

_GENERIC = re.compile(
    r"^(正文|核心内容|补充内容|教材内容|课程内容|Content|Core content|"
    r"第[一二三四五六七八九十百0-9.]+节\s*正文|知识点\s*\d+)$", re.I
)


def _digest(pages: Iterable, limit_chars: int = 220) -> str:
    rows: list[str] = []
    for page in pages:
        text = re.sub(r"\s+", " ", (page.text or "")).strip()
        rows.append(f"P{page.page_no}: {text[:limit_chars]}")
    return "\n".join(rows)


def _normalize_pages(value) -> list[int] | None:
    if not isinstance(value, list) or not value:
        return None
    out: list[int] = []
    for item in value:
        try:
            n = int(item)
        except Exception:
            return None
        if n <= 0:
            return None
        out.append(n)
    return out


def validate_plan(sections: list[dict], page_count: int, *, max_sections: int = 24) -> list[tuple[str, list[int]]] | None:
    if not isinstance(sections, list) or not (2 <= len(sections) <= max_sections):
        return None
    parsed: list[tuple[str, list[int]]] = []
    titles: set[str] = set()
    all_pages: list[int] = []
    last_end = 0
    for item in sections:
        if not isinstance(item, dict):
            return None
        title = str(item.get("title") or "").strip()
        pages = _normalize_pages(item.get("pages"))
        if not title or len(title) > 40 or _GENERIC.match(title) or title in titles:
            return None
        if pages is None:
            return None
        page_start, page_end = min(pages), max(pages)
        if pages != list(range(page_start, page_end + 1)):
            return None
        if page_start <= last_end:
            return None
        last_end = page_end
        titles.add(title)
        all_pages.extend(pages)
        parsed.append((title, pages))
    if sorted(all_pages) != list(range(1, page_count + 1)):
        return None
    return parsed


def plan_with_llm(
    client,
    ledger,
    fallback: list[tuple[str, list[int]]],
    *,
    requirements: dict | None = None,
    gen_lang: str = "zh",
) -> list[tuple[str, list[int]]]:
    """返回经验证的教学单元；任何异常都返回 fallback，不影响生成。"""
    if ledger.page_count < 4:
        return fallback
    req = requirements or {}
    focus = str(req.get("summary") or "")[:500]
    must = "、".join(str(x.get("label") or "") for x in (req.get("must_cover") or []))[:400]
    prompt = f"""资料共 {ledger.page_count} 页。请把它规划成 3–12 个教学单元，按学生应该学习的先后顺序排列。

用户需求：{focus or '无额外要求'}
必须覆盖的考点：{must or '按资料实际内容提取'}

要求：
- 每个单元是一个连续、完整的知识主题，不是“第1-5页”这种页码块；
- 每个单元给一个具体的中文标题（英文/繁体按目标语言），不要“正文/核心内容/知识点1”；
- 标题要体现该单元的核心概念、方法或考点，单元之间体现递进；
- 页码必须连续、不重叠、不遗漏，合起来完整覆盖 1..{ledger.page_count}；
- 保持页码顺序，不要为了逻辑好看而打乱资料顺序；
- 不要编造资料没有的章节；一个单元建议 3–10 页，短资料可更少。

资料页摘要：
{_digest(ledger.pages[:120])}

只输出 JSON：{{"sections":[{{"title":"单元标题","pages":[1,2,3]}}]}}"""
    try:
        data = client.json(
            "你是大学课程教学设计编辑。只根据给出的资料页摘要规划教学单元，不编造内容；页码必须完整覆盖。",
            prompt,
            max_tokens=1800,
            temperature=0.2,
        )
    except Exception:
        return fallback
    sections = data.get("sections") if isinstance(data, dict) else None
    validated = validate_plan(sections, ledger.page_count)
    if not validated:
        return fallback
    return validated
