"""Apply a page range to non-lecture modules by creating a scoped artifact."""
from __future__ import annotations

import tempfile
from pathlib import Path

from . import page_scope, service, source_artifact


def create_scoped_artifact(material_id: str, page_spec: str) -> dict:
    path = service.artifact_path(material_id)
    if path is None:
        raise FileNotFoundError(f"artifact 不存在：{material_id}")
    source = next((p for p in (path / "source").glob("*") if p.is_file()), None)
    if source is None:
        raise FileNotFoundError("artifact 缺少 source")
    with tempfile.TemporaryDirectory(prefix="tf_scope_art_") as td:
        target = Path(td) / f"scoped_{source.stem}.pdf"
        info = page_scope.slice_pdf(source, target, page_spec)
        made = source_artifact.create_exam_source(target, title=f"{material_id} 页码范围 {page_spec}")
    return {"id": made["id"], "page_count": made["pages"], "scope": info}


def wrap(handler, page_spec: str = "all"):
    """Return a handler that runs on a scoped artifact when a range is set."""
    if not page_spec or str(page_spec).strip().lower() in ("all", "全部"):
        return handler

    def scoped(material: dict) -> dict:
        made = create_scoped_artifact(material["id"], page_spec)
        result = handler({**material, "id": made["id"]}) or {}
        result = dict(result)
        result["scope"] = {"requested": page_spec, "page_count": made["page_count"],
                           "scoped_artifact": made["id"]}
        return result
    return scoped
