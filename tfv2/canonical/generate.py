"""Slot generation: every fact must be consumed by exactly one block."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from .model import CanonicalDocument, Fact


class GeneratedBlock(BaseModel):
    fact_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    kind: str = "paragraph"


class SlotResult(BaseModel):
    blocks: list[GeneratedBlock] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    status: str = "partial"

    @property
    def coverage(self) -> float:
        total = len(self.blocks) + len(self.missing)
        return round(len(self.blocks) / max(1, total), 4)


def _batch_prompt(facts: list[Fact]) -> str:
    payload = [{"fact_id": f.fact_id, "page": f.page, "kind": f.kind.value, "text": f.text}
               for f in facts]
    return (
        "为每条事实写一个教材 block。必须返回 JSON："
        '{"blocks":[{"fact_id":"...","text":"...","kind":"paragraph"}]}。'
        "每个 fact_id 恰好出现一次；不得新增 fact_id；只输出 JSON。\n"
        + json.dumps(payload, ensure_ascii=False)
    )


def generate_slots(doc: CanonicalDocument, client: Any, *, batch_size: int = 8,
                   fact_ids: list[str] | None = None) -> SlotResult:
    selected = [f for f in doc.facts if fact_ids is None or f.fact_id in set(fact_ids)]
    by_id = {f.fact_id: f for f in selected}
    blocks: list[GeneratedBlock] = []
    seen: set[str] = set()
    for i in range(0, len(selected), batch_size):
        batch = selected[i:i + batch_size]
        try:
            data = client.json(
                "你是教材讲解员。只依据给定事实写 block，不编造；只输出 JSON。",
                _batch_prompt(batch), max_tokens=4096, temperature=0.2,
            )
        except Exception:
            continue
        for item in (data.get("blocks") if isinstance(data, dict) else []) or []:
            fid = str(item.get("fact_id") or "")
            text = str(item.get("text") or "").strip()
            if fid in by_id and fid not in seen and text:
                seen.add(fid)
                blocks.append(GeneratedBlock(fact_id=fid, text=text, kind=str(item.get("kind") or "paragraph")))
    missing = sorted(set(by_id) - seen)
    return SlotResult(blocks=blocks, missing=missing,
                      status="validated" if not missing else "partial")
