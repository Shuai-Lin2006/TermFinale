"""多资料组合：拼接（自然融合）或不拼接（N 份资料 → N 份讲义）。

两种拼接模式必须分清楚，不允许糊在一起：

- ``fuse``   ：自然融合。统一主题与章节、章级过渡、同名概念去重，一份讲义、文字可搜索。
  （tfv2/product/fusion.py）
- ``append`` ：合订本。每份资料各自成精读页段，再按顺序拼成一个 PDF。
  只为兼容旧入口保留；它不是“融合”，报告里会明确标注 mode=append。

不拼接时保持 N → N：每份资料单独出一份讲义，互不影响。
"""
from __future__ import annotations

import json

from tfv2.product import service
from tfv2.product.batch_merge import merge_chunks
from tfv2.product.source_digest import build_source_digest


def combine_materials(
    output_id: str,
    materials: list[dict],
    merge: bool = True,
    *,
    mode: str = "fuse",
    title: str = "",
    course: str = "",
    author: bool = True,
    client=None,
    progress=None,
) -> dict:
    if not materials:
        raise ValueError("至少选一份资料")
    normalized: list[dict] = []
    for item in materials:
        aid = str(item.get("artifact_id") or "")
        pages = [int(x) for x in (item.get("pages") or [])]
        if not aid or not pages:
            raise ValueError("每份资料必须给 artifact_id 和 pages")
        normalized.append({**item, "artifact_id": aid, "pages": pages})

    if not merge:
        # 不拼接：N 份资料 → N 份讲义，各自独立，页码互不干扰。
        ids = []
        for i, item in enumerate(normalized, 1):
            cid = f"{output_id}-m{i}"
            build_source_digest(item["artifact_id"], item["pages"], cid,
                                progress=None)
            ids.append(cid)
        return {"merge": False, "mode": "separate", "artifacts": ids,
                "materials": [x["artifact_id"] for x in normalized]}

    if mode == "append":
        ids = []
        for i, item in enumerate(normalized, 1):
            cid = f"{output_id}-m{i}"
            build_source_digest(item["artifact_id"], item["pages"], cid)
            ids.append(cid)
        pdf = merge_chunks(output_id, ids)
        path = service.artifact_path(output_id)
        if path is not None:
            m = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
            m["merged_from"] = [str(x.get("artifact_id")) for x in normalized]
            m["merge_mode"] = "append"
            (path / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"merge": True, "mode": "append", "artifact_id": output_id, "pdf": str(pdf)}

    from tfv2.product.fusion import fuse_materials

    result = fuse_materials(output_id, normalized, title=title, course=course,
                            author=author, client=client, progress=progress)
    path = service.artifact_path(output_id)
    if path is not None and (path / "manifest.json").is_file():
        m = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        m["merged_from"] = [str(x.get("artifact_id")) for x in normalized]
        m["merge_mode"] = "fuse"
        (path / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    result["merge"] = True
    result["mode"] = "fuse"
    return result
