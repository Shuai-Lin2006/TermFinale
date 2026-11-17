"""Execute a module against only the materials selected for that module.

This is the seam between workspace selection and real task runners. It writes
one output per material, so a lecture from A can never overwrite an extraction
from B.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from . import workspace


class ModuleRunError(RuntimeError):
    pass


def run(root: str | Path, module: str, handler: Callable[[dict], dict],
        out_root: str | Path | None = None) -> dict:
    root = Path(root)
    if module not in workspace.MODULES:
        raise ModuleRunError(f"未知模块：{module}")
    selected = workspace.resolve(root, module)
    if not selected:
        raise ModuleRunError(f"模块 {module} 还没有选资料")
    out = Path(out_root) if out_root else root / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for material in selected:
        started = time.time()
        try:
            result = handler(material) or {}
            status = result.get("status") if result.get("status") in ("done", "validated", "partial", "no_questions", "rejected") else "done"
            error = ""
        except Exception as exc:  # noqa: BLE001
            result = {}
            status = "failed"
            error = f"{type(exc).__name__}: {exc}"
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in material["id"])[:80]
        target = out / module / f"{safe}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({
            "module": module, "material_id": material["id"],
            "material_title": material.get("title") or material["id"],
            "status": status, "error": error, "seconds": round(time.time() - started, 2),
            "result": result,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append({"material_id": material["id"], "status": status,
                     "output": str(target), "error": error})
    return {"module": module, "materials": rows,
            "selected": [m["id"] for m in selected],
            "all_done": all(r["status"] in ("done", "validated") for r in rows)}
