"""本地授权图库适配：只选原图，不生成。"""
from __future__ import annotations
import json
from pathlib import Path


def load_index(root: Path) -> list[dict]:
    p = root / "index.json"
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def pick(root: Path, *, tags: list[str] | None = None, page: int | None = None) -> dict | None:
    items = load_index(root)
    tags = [str(x) for x in (tags or []) if str(x).strip()]
    if page is not None:
        for it in items:
            if page in [int(x) for x in (it.get("source_pages") or [])]:
                return it
    for it in items:
        hay = " ".join([str(it.get("title") or ""), " ".join(it.get("tags") or []), str(it.get("id") or "")])
        if tags and all(t in hay for t in tags):
            return it
    return items[0] if items and not tags else None
