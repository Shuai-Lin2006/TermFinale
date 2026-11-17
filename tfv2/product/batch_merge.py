"""把多个分批生成产物合并成一份讲义。

每个 chunk 自身仍是 16 页以内的产物；合并只做页码重映射和 sections 拼接，
不重新生成正文。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pymupdf

from tfv2.build import build_project
from tfv2.product import service


def merge_chunks(output_id: str, chunk_ids: list[str]) -> Path:
    if not chunk_ids:
        raise ValueError("没有分批产物")
    from core import paths
    dirs = [service.artifact_path(x) or (paths.data_dir() / "previews" / x) for x in chunk_ids]
    if any(not d.is_dir() for d in dirs):
        raise FileNotFoundError("分批产物不存在")
    dirs = [d for d in dirs if d.is_dir()]

    dst = service.artifact_path(output_id) or (dirs[0].parent / output_id)
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "source").mkdir(parents=True)
    (dst / "source_assets").mkdir()

    merged = pymupdf.open()
    rows: list[dict] = []
    sections: list[dict] = []
    offset = 0
    for d in dirs:
        sp = next((d / "source").glob("*.pdf"))
        src = pymupdf.open(str(sp))
        merged.insert_pdf(src)
        src.close()
        raw = json.loads((d / "source_pages.json").read_text(encoding="utf-8"))
        part = raw.get("pages") or raw
        for row in part:
            x = dict(row)
            x["page"] = offset + int(x.get("page") or 1)
            rows.append(x)
        for sec in json.loads((d / "sections.json").read_text(encoding="utf-8")):
            s = dict(sec)
            s["id"] = f"m{offset}-{s.get('id')}"
            for b in s.get("blocks") or []:
                for r in b.get("source_refs") or []:
                    if r.get("page_start"):
                        r["page_start"] = offset + int(r["page_start"])
                    if r.get("page_end"):
                        r["page_end"] = offset + int(r["page_end"])
            for r in s.get("source_refs") or []:
                if r.get("page_start"):
                    r["page_start"] = offset + int(r["page_start"])
                if r.get("page_end"):
                    r["page_end"] = offset + int(r["page_end"])
            sections.append(s)
        offset += len(part)
    merged.save(str(dst / "source" / "scoped.pdf"))
    merged.close()

    (dst / "source_pages.json").write_text(json.dumps(
        {"version": 1, "material": dirs[0].name, "page_count": len(rows), "pages": rows},
        ensure_ascii=False, indent=2), encoding="utf-8")
    pr = json.loads((dirs[0] / "project.json").read_text(encoding="utf-8"))
    pr.update({
        "id": output_id,
        "page_count": len(rows),
        "scope_pages": list(range(1, len(rows) + 1)),
        "source_file": "source/scoped.pdf",
        "sections_files": ["sections.json"],
    })
    (dst / "project.json").write_text(json.dumps(pr, ensure_ascii=False, indent=2), encoding="utf-8")
    (dst / "sections.json").write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
    build_project(dst / "project.json", pdf=True)
    return dst / "lecture.pdf"
