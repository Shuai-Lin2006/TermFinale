"""Anchor-based synthesis: free prose is allowed, every fact must be claimed."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from .model import Fact, SectionPlan


class SynthesisBlock(BaseModel):
    text: str = Field(min_length=1)
    covers: list[str] = Field(default_factory=list)


class SynthesisSection(BaseModel):
    plan_id: str
    blocks: list[SynthesisBlock] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    status: str = "partial"

    @property
    def coverage(self) -> float:
        covered = {x for b in self.blocks for x in b.covers}
        total = len(covered) + len(self.missing)
        return round(len(covered) / max(1, total), 4)


def _prompt(plan: SectionPlan, facts: list[Fact], missing_only: list[str] | None = None) -> str:
    anchors = [{"fact_id": f.fact_id, "kind": f.kind.value, "text": f.text}
               for f in facts if f.fact_id in set(plan.fact_ids)
               and (missing_only is None or f.fact_id in set(missing_only))]
    return (
        "把本节的锚点事实写成连贯教材，允许过渡、推导、例子，但每个 fact_id 必须在 covers 中出现；"
        "不得新增 fact_id；只输出 JSON："
        '{"blocks":[{"text":"...","covers":["fact_id"]}]}。\n'
        + json.dumps({"plan": plan.plan_id, "pages": [plan.page_start, plan.page_end],
                      "anchors": anchors}, ensure_ascii=False)
    )


def synthesize_section(plan: SectionPlan, facts: list[Fact], client: Any) -> SynthesisSection:
    try:
        data = client.json("你是教材作者；写连贯讲解，不丢锚点；只输出 JSON。",
                           _prompt(plan, facts), max_tokens=6000, temperature=0.3)
        blocks = [SynthesisBlock(text=str(b.get("text") or "").strip(),
                                 covers=[str(x) for x in b.get("covers") or []])
                  for b in (data.get("blocks") if isinstance(data, dict) else []) or []
                  if str(b.get("text") or "").strip()]
    except Exception:
        blocks = []
    allowed = set(plan.fact_ids)
    covered = {x for b in blocks for x in b.covers if x in allowed}
    missing = sorted(allowed - covered)
    return SynthesisSection(plan_id=plan.plan_id, blocks=blocks, missing=missing,
                            status="validated" if not missing else "partial")

def fill_missing(section: SynthesisSection, slots: dict[str, str]) -> SynthesisSection:
    """Free prose first; deterministic slot fallback only for missing anchors."""
    covered = {x for b in section.blocks for x in b.covers}
    blocks = list(section.blocks)
    for fid in section.missing:
        if fid in covered or not slots.get(fid):
            continue
        blocks.append(SynthesisBlock(text=slots[fid], covers=[fid]))
        covered.add(fid)
    missing = sorted(set(section.missing) - covered)
    return section.model_copy(update={"blocks": blocks, "missing": missing,
                                      "status": "validated" if not missing else "partial"})
