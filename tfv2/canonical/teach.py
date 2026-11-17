"""Teaching contract: roles + anchors, while prose stays free."""
from __future__ import annotations

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .model import Fact, SectionPlan


class Role(str, Enum):
    DEFINITION = "definition"
    EXPLANATION = "explanation"
    FORMULA = "formula"
    DERIVATION = "derivation"
    EXAMPLE = "example"
    PITFALL = "pitfall"
    SUMMARY = "summary"


class TeachingBlock(BaseModel):
    role: Role
    text: str = Field(min_length=1)
    covers: list[str] = Field(default_factory=list)


class TeachingSection(BaseModel):
    plan_id: str
    blocks: list[TeachingBlock] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    missing_roles: list[str] = Field(default_factory=list)
    status: str = "partial"


def required_roles(facts: list[Fact]) -> list[Role]:
    roles = [Role.DEFINITION, Role.EXPLANATION, Role.EXAMPLE, Role.PITFALL, Role.SUMMARY]
    if any(f.kind.value == "formula" for f in facts):
        roles.extend([Role.FORMULA, Role.DERIVATION])
    return roles


def _prompt(plan: SectionPlan, facts: list[Fact], roles: list[Role]) -> str:
    anchors = [{"fact_id": f.fact_id, "kind": f.kind.value, "text": f.text}
               for f in facts if f.fact_id in set(plan.fact_ids)]
    return (
        "按教学结构写本节，允许自由表达，但必须："
        "1) 每个 fact_id 至少出现在一个 block 的 covers；"
        "2) 每个 role 至少出现一次；只输出 JSON："
        '{"blocks":[{"role":"definition|explanation|formula|derivation|example|pitfall|summary",'
        '"text":"...","covers":["fact_id"]}]}。\n'
        + json.dumps({"roles": [r.value for r in roles], "anchors": anchors}, ensure_ascii=False)
    )


def synthesize_teaching(plan: SectionPlan, facts: list[Fact], client: Any) -> TeachingSection:
    roles = required_roles([f for f in facts if f.fact_id in set(plan.fact_ids)])
    try:
        data = client.json("你是教材作者；按结构写，不丢锚点；只输出 JSON。",
                           _prompt(plan, facts, roles), max_tokens=7000, temperature=0.3)
    except Exception:
        data = {}
    blocks: list[TeachingBlock] = []
    for item in (data.get("blocks") if isinstance(data, dict) else []) or []:
        text = str(item.get("text") or "").strip()
        try:
            role = Role(str(item.get("role") or ""))
        except ValueError:
            continue
        if text:
            blocks.append(TeachingBlock(role=role, text=text,
                                        covers=[str(x) for x in item.get("covers") or []]))
    covered = {x for b in blocks for x in b.covers if x in set(plan.fact_ids)}
    missing_facts = sorted(set(plan.fact_ids) - covered)
    present = {b.role for b in blocks}
    missing_roles = [r.value for r in roles if r not in present]
    return TeachingSection(plan_id=plan.plan_id, blocks=blocks,
                           missing_facts=missing_facts, missing_roles=missing_roles,
                           status="validated" if not missing_facts and not missing_roles else "partial")

def fill_missing_facts(section: TeachingSection, slots: dict[str, str]) -> TeachingSection:
    covered = {x for b in section.blocks for x in b.covers}
    blocks = list(section.blocks)
    for fid in section.missing_facts:
        if fid in covered or not slots.get(fid):
            continue
        blocks.append(TeachingBlock(role=Role.EXPLANATION, text=slots[fid], covers=[fid]))
        covered.add(fid)
    missing = sorted(set(section.missing_facts) - covered)
    return section.model_copy(update={"blocks": blocks, "missing_facts": missing,
                                      "status": "validated" if not missing and not section.missing_roles else "partial"})
