"""把用户填写的任意自然语言要求，先交给需求理解 Agent 结构化。

这里不是关键词过滤器：用户说“全都是重点”“每节先给结构图”“不要考微分电路”，
都应当被理解为覆盖范围、必讲点、必避点或写作指令。只有模型不可用时才走
保守兜底，且兜底也不会把泛化短句当成正文必须原样出现的字符串。
"""
from __future__ import annotations

import json
import re
from typing import Any

from tfv2.llm.client import DeepSeekClient, LLMError

_GENERIC = {
    "全都是重点", "全是重点", "全部都是重点", "全部是重点", "全考", "全都考",
    "全部考", "全都要", "全部要", "无", "没有", "没有重点", "无重点", "无特别重点",
}

_SYSTEM = """你是 TermFinale 的学习需求理解 Agent，不是关键词过滤器。
请把用户填写的重点、明确不考、补充要求理解为真实学习意图，并输出 JSON。
规则：
1. 用户说“全都是重点/全考/所有都考”时，coverage=all，must_cover 不要填这句话本身；
2. 用户写具体概念、章节、公式、题型时，提取为 must_cover，保留权重；同一概念可给 aliases；
3. 用户说“不要/不考/跳过”时，提取为 must_not；不要把它误放进 must_cover；
4. 其他写作要求（结构、语气、推导速度、类比、排版等）放进 instructions；
5. 用户写“无/没有”时忽略，不要制造要求；
6. 不要用字符串包含作为判断标准；要理解同义表达和条件。
只输出 JSON，不要 Markdown，不要解释。"""

_SCHEMA = """输出结构：
{
  "coverage": "all" | "focus",
  "must_cover": [{"label": "概念", "weight": 1, "aliases": ["同义写法"]}],
  "must_not": [{"label": "概念", "aliases": ["同义写法"]}],
  "instructions": ["可执行写作/结构要求"],
  "ignored": ["被忽略的泛化输入原文"],
  "summary": "一句话概括用户要求"
}"""


def _clean_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


def _is_generic(term: str) -> bool:
    t = re.sub(r"[\s，,。；;、:：]+", "", term or "")
    if not t or t in _GENERIC:
        return True
    return any(t.startswith(x) and len(t) <= len(x) + 3 for x in ("全都是重点", "全是重点", "全考", "全部都是重点"))


def _fallback(key_points: str, excluded: str, custom_prompt: str) -> dict:
    cover = []
    for token in re.split(r"[\n,，、;；]+", key_points or ""):
        token = token.strip()
        if not token or _is_generic(token):
            continue
        parts = re.split(r"[=＝:：]", token, maxsplit=1)
        label = parts[0].strip()
        if not label or _is_generic(label):
            continue
        weight = 3
        if len(parts) == 2:
            try:
                weight = max(1, min(5, int(re.sub(r"[^0-9]", "", parts[1]) or 3)))
            except Exception:
                weight = 3
        cover.append({"label": label, "weight": weight, "aliases": []})
    avoid = []
    for token in re.split(r"[\n,，、;；]+", excluded or ""):
        token = token.strip()
        if token and not _is_generic(token):
            avoid.append({"label": token, "aliases": []})
    instructions = []
    if custom_prompt.strip() and not _is_generic(custom_prompt):
        instructions.append(custom_prompt.strip())
    return {
        "coverage": "all" if not cover else "focus",
        "must_cover": cover,
        "must_not": avoid,
        "instructions": instructions,
        "ignored": [],
        "summary": "按用户资料范围生成" if not cover else "聚焦用户指定的重点",
        "source": "heuristic",
    }


def _normalize(data: dict, raw: tuple[str, str, str]) -> dict:
    must_cover = []
    for item in data.get("must_cover") or []:
        if isinstance(item, str):
            item = {"label": item}
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label or _is_generic(label):
            continue
        try:
            weight = max(1, min(5, int(item.get("weight") or 3)))
        except Exception:
            weight = 3
        must_cover.append({"label": label[:120], "weight": weight,
                           "aliases": _clean_list(item.get("aliases"))[:6]})
    must_not = []
    for item in data.get("must_not") or []:
        if isinstance(item, str):
            item = {"label": item}
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if label and not _is_generic(label):
            must_not.append({"label": label[:120], "aliases": _clean_list(item.get("aliases"))[:6]})
    coverage = str(data.get("coverage") or "").lower()
    if coverage not in ("all", "focus"):
        coverage = "all" if not must_cover else "focus"
    instructions = [x[:300] for x in _clean_list(data.get("instructions")) if not _is_generic(x)]
    ignored = [x[:120] for x in _clean_list(data.get("ignored"))]
    return {
        "coverage": coverage,
        "must_cover": must_cover,
        "must_not": must_not,
        "instructions": instructions,
        "ignored": ignored,
        "summary": str(data.get("summary") or "")[:300],
        "source": "agent",
        "raw": {"key_points": raw[0], "excluded": raw[1], "custom_prompt": raw[2]},
    }


def interpret_requirements(
    client: DeepSeekClient,
    *,
    key_points: str = "",
    excluded: str = "",
    custom_prompt: str = "",
    title: str = "",
    course: str = "",
    target_score: int | None = None,
    days_left: int | None = None,
    foundation: str = "",
    persona: str = "",
    gen_lang: str = "zh",
) -> dict:
    raw = (key_points or "", excluded or "", custom_prompt or "")
    if not any(x.strip() for x in raw):
        return {"coverage": "all", "must_cover": [], "must_not": [], "instructions": [],
                "ignored": [], "summary": "", "source": "empty", "raw": {}}
    user = (
        f"资料标题：{title}\n课程：{course}\n目标分：{target_score}\n剩余天数：{days_left}\n"
        f"基础：{foundation}\n人设：{persona}\n生成语言：{gen_lang}\n"
        f"用户填写的重点（可能是一整句话）：{key_points or '（空）'}\n"
        f"用户填写的明确不考：{excluded or '（空）'}\n"
        f"用户填写的补充要求：{custom_prompt or '（空）'}\n\n"
        + _SCHEMA
    )
    try:
        data = client.json(_SYSTEM, user, max_tokens=1200, temperature=0.1)
        if not isinstance(data, dict):
            return _fallback(*raw)
        return _normalize(data, raw)
    except LLMError:
        return _fallback(*raw)
    except Exception:
        return _fallback(*raw)


def requirement_prompt(req: dict) -> str:
    if not req:
        return ""
    lines = []
    if req.get("coverage") == "all":
        lines.append("覆盖范围：全部资料；不要只挑关键词，也不要把“全是重点”当成一个必须原样出现的词。")
    cover = req.get("must_cover") or []
    if cover:
        lines.append("用户明确要覆盖的内容（语义理解，不要求逐字复现）：")
        for x in cover:
            alias = f"（同义：{'、'.join(x.get('aliases') or [])}）" if x.get("aliases") else ""
            lines.append(f"- {x.get('label')}，权重 {x.get('weight', 3)}/5{alias}")
    avoid = req.get("must_not") or []
    if avoid:
        lines.append("用户明确不考/不要写：" + "、".join(x.get("label", "") for x in avoid))
    for x in req.get("instructions") or []:
        lines.append(f"- 额外要求：{x}")
    return "\n".join(lines)


def requirement_focus(req: dict) -> list[str]:
    return [f"{x.get('label')}（权重 {x.get('weight', 3)}）" for x in (req.get("must_cover") or [])]
