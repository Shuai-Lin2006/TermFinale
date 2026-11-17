"""Manual question-bank import: source-grounded fallback for past exams.

CSV/JSON import never invents questions: every row must have a stem; optional
answer/analysis/page are kept as-is. Duplicate stems are skipped.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


def _norm(text: str) -> str:
    return "".join(str(text or "").split()).lower()


def _row(raw: dict) -> dict:
    stem = str(raw.get("stem") or raw.get("question") or raw.get("题干") or "").strip()
    if not stem:
        raise ValueError("题目缺少 stem/题干")
    page = raw.get("page") or raw.get("source_page") or raw.get("页码") or ""
    try:
        page = int(page) if str(page).strip().isdigit() else None
    except Exception:
        page = None
    return {
        "stem": stem,
        "qtype": str(raw.get("qtype") or raw.get("type") or raw.get("题型") or "short_answer"),
        "answer": str(raw.get("answer") or raw.get("答案") or ""),
        "analysis": str(raw.get("analysis") or raw.get("解析") or ""),
        "source_page": page,
        "material_id": str(raw.get("material_id") or raw.get("资料") or ""),
        "tags": [x for x in str(raw.get("tags") or raw.get("标签") or "").replace("；", ",").split(",") if x.strip()],
    }


def load(path: str | Path) -> list[dict]:
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".csv":
        rows = list(csv.DictReader(text.splitlines()))
    else:
        data = json.loads(text)
        rows = data if isinstance(data, list) else (data.get("items") or [])
    out, seen = [], set()
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        item = _row(raw)
        key = _norm(item["stem"])[:200]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def save(root: str | Path, items: list[dict]) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    target = root / "question_bank.json"
    target.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def import_to_workspace(root: str | Path, source: str | Path) -> dict:
    items = load(source)
    save(root, items)
    return {"imported": len(items), "bank": str(Path(root) / "question_bank.json")}


def validated(items_: list[dict]) -> bool:
    """A manual bank is validated only when every item has stem, answer, page."""
    if not items_:
        return False
    for x in items_:
        if not str(x.get("stem") or "").strip():
            return False
        if not str(x.get("answer") or "").strip():
            return False
        if not x.get("source_page"):
            return False
    return True


def items(root: str | Path, material_id: str | None = None) -> list[dict]:
    path = Path(root) / "question_bank.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("items") if isinstance(data, dict) else []
    except Exception:
        return []
    if material_id is None:
        return rows or []
    return [x for x in rows or [] if not x.get("material_id") or x.get("material_id") == material_id]
