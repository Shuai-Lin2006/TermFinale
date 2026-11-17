"""从 artifact 生成统一页单元，供讲义/提取/练习/出卷共用。"""
from __future__ import annotations

import json
from pathlib import Path

from tfv2.domain.page_unit import build_page_unit
from tfv2.product.service import artifact_path


def units_for_artifact(aid: str) -> list[dict]:
    path = artifact_path(aid)
    if path is None:
        raise FileNotFoundError("artifact not found")
    raw = json.loads((path / "source_pages.json").read_text(encoding="utf-8"))
    rows = raw.get("pages") or raw
    out = []
    for i, row in enumerate(rows, 1):
        unit = build_page_unit(i, str(row.get("text") or ""))
        item = unit.__dict__.copy()
        item["source"] = {"material": aid, "page": i}
        out.append(item)
    return out
