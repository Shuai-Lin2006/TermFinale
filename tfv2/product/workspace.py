"""Material workspace: one course, many materials, four independent modules.

The same course may have a lecture source, an extraction source and an exam
source. Selecting a material for one module must never change another module.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

MODULES = ("lecture", "extract", "questions", "exam")


class WorkspaceError(ValueError):
    pass


def create(root: str | Path, name: str, materials: list[dict]) -> dict:
    if not name.strip():
        raise WorkspaceError("工作区名称不能为空")
    ids = [str(m.get("id") or "").strip() for m in materials]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise WorkspaceError("资料 id 不能为空或重复")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    data = {
        "name": name.strip(),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "materials": [
            {"id": str(m["id"]), "title": str(m.get("title") or m["id"]),
             "path": str(m.get("path") or ""), "pages": int(m.get("pages") or 0)}
            for m in materials
        ],
        # Each module has its own selection. Empty = not selected.
        "modules": {m: [] for m in MODULES},
    }
    (root / "workspace.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def load(root: str | Path) -> dict:
    path = Path(root) / "workspace.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise WorkspaceError(f"工作区不存在或损坏：{exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("materials"), list):
        raise WorkspaceError("工作区结构不合法")
    data.setdefault("modules", {m: [] for m in MODULES})
    return data


def save(root: str | Path, data: dict) -> None:
    (Path(root) / "workspace.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def select(root: str | Path, module: str, material_ids: list[str]) -> dict:
    if module not in MODULES:
        raise WorkspaceError(f"未知模块：{module}")
    data = load(root)
    known = {m["id"] for m in data["materials"]}
    picked = [str(x) for x in material_ids]
    unknown = [x for x in picked if x not in known]
    if unknown:
        raise WorkspaceError("资料不属于当前工作区：" + ", ".join(unknown))
    if len(picked) != len(set(picked)):
        raise WorkspaceError("同一模块不能重复选同一资料")
    if module == "lecture" and len(picked) > 1:
        raise WorkspaceError("讲义模块只能选一份资料")
    if module == "exam" and len(picked) > 1:
        raise WorkspaceError("出卷模块只能选一份主资料")
    data["modules"][module] = picked
    save(root, data)
    return data


def resolve(root: str | Path, module: str) -> list[dict]:
    data = load(root)
    if module not in MODULES:
        raise WorkspaceError(f"未知模块：{module}")
    by_id = {m["id"]: m for m in data["materials"]}
    return [by_id[x] for x in data["modules"].get(module, []) if x in by_id]


def independence_report(root: str | Path) -> dict:
    data = load(root)
    return {
        "modules": {m: list(data["modules"].get(m, [])) for m in MODULES},
        "same_source": {
            "lecture_extract": data["modules"].get("lecture") == data["modules"].get("extract"),
            "extract_exam": data["modules"].get("extract") == data["modules"].get("exam"),
        },
    }
