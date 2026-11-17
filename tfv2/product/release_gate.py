"""Release gate: four modules must be validated; partial is not shippable."""
from __future__ import annotations

import json
from pathlib import Path

MODULES = ("lecture", "extract", "questions", "exam")


def _rows(path: Path) -> list[dict]:
    out = []
    if not path.is_dir():
        return out
    for p in sorted(path.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                out.append(data)
        except Exception:
            continue
    return out


def evaluate(workspace_root: str | Path, *, ui_ready: bool = False,
             benchmark_passed: bool = False) -> dict:
    root = Path(workspace_root)
    modules = {}
    blockers = []
    for module in MODULES:
        rows = _rows(root / "outputs" / module)
        statuses = []
        for row in rows:
            res = row.get("result") if isinstance(row.get("result"), dict) else {}
            status = str(res.get("status") or row.get("status") or "")
            if status == "done" and res.get("gate_passed"):
                status = "validated"
            statuses.append(status)
        ok = bool(rows) and all(s == "validated" for s in statuses) and len(rows) >= 2
        modules[module] = {"count": len(rows), "statuses": statuses, "validated": ok}
        if not rows:
            blockers.append(f"{module}: 无产物")
        elif len(rows) < 2:
            blockers.append(f"{module}: 只有 {len(rows)} 份资料，要求 2 份")
        elif not all(s == "validated" for s in statuses):
            blockers.append(f"{module}: 存在非 validated 状态 {sorted(set(statuses))}")
    if not ui_ready:
        blockers.append("UI: 未完成")
    if not benchmark_passed:
        blockers.append("基准: 未通过开源基准")
    return {"release": not blockers, "modules": modules, "blockers": blockers,
            "ui_ready": ui_ready, "benchmark_passed": benchmark_passed}
