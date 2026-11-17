"""讲义库：扫描 docs/evidence/*/manifest.json，给阅读器提供 artifact 列表。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel

_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class Artifact(BaseModel):
    id: str
    title: str
    directory: str
    html_url: str
    pdf_url: str | None = None
    page_count: int | None = None
    coverage: str | None = None
    gate_passed: bool | None = None
    sections: int | None = None
    figures: int | None = None
    updated_at: str | None = None
    manifest_path: str


def _read_title(manifest: dict, manifest_path: Path) -> str:
    for key in ("chapter", "artifact"):
        val = manifest.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    readme = manifest_path.with_name("README.md")
    if readme.is_file():
        for line in readme.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return manifest_path.parent.name


def discover(root: str | Path) -> list[Artifact]:
    base = Path(root) / "docs" / "evidence"
    out: list[Artifact] = []
    if not base.is_dir():
        return out
    for manifest_path in sorted(base.glob("*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        aid = manifest_path.parent.name
        if not _ID.match(aid):
            continue
        html_path = manifest_path.parent / "lecture.html"
        if not html_path.is_file():
            continue
        pdf_path = manifest_path.parent / "lecture.pdf"
        gate = manifest.get("gate") or {}
        out.append(Artifact(
            id=aid,
            title=_read_title(manifest, manifest_path),
            directory=str(manifest_path.parent),
            html_url=f"/docs/evidence/{aid}/lecture.html",
            pdf_url=f"/docs/evidence/{aid}/lecture.pdf" if pdf_path.is_file() else None,
            page_count=manifest.get("pdf_pages") or manifest.get("page_count"),
            coverage=manifest.get("scope_coverage") or manifest.get("material_coverage"),
            gate_passed=gate.get("passed") if isinstance(gate, dict) else None,
            sections=manifest.get("section_count") or manifest.get("sections"),
            figures=manifest.get("figures") or (manifest.get("figure_report") or {}).get("figures"),
            updated_at=manifest.get("generated_at"),
            manifest_path=str(manifest_path),
        ))
    out.sort(key=lambda x: (x.page_count or 0, x.updated_at or ""), reverse=True)
    return out
