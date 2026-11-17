"""Optional Docling backend.

Docling is deliberately not a hard dependency: its runtime + model cache is
~2GB and cannot be shipped inside the current desktop bundle. When
``TERMFINALE_DOCLING_PYTHON`` points at a Python environment with docling
installed, the generation pipeline invokes this module in a subprocess.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

_TABLE_BLOCK = re.compile(r"(?:^\|.*\|\s*$[\n\r]*)+", flags=re.M)


def _bbox(prov: dict, page_height: float) -> list[float] | None:
    box = prov.get("bbox") if isinstance(prov, dict) else None
    if not isinstance(box, dict):
        return None
    try:
        left = float(box.get("l")); right = float(box.get("r"))
        top = float(box.get("t")); bottom = float(box.get("b"))
    except Exception:
        return None
    # Docling PDF coordinates use BOTTOMLEFT; our layout model uses TOPLEFT.
    return [round(left, 2), round(page_height - top, 2), round(right, 2), round(page_height - bottom, 2)]


def convert_pdf(pdf_path: str | Path, out_dir: str | Path) -> dict:
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    from docling.document_converter import DocumentConverter

    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    doc = DocumentConverter().convert(str(pdf_path)).document
    raw = doc.export_to_dict()
    page_sizes = {}
    for key, value in (raw.get("pages") or {}).items():
        try:
            size = value.get("size") or {}
            page_sizes[int(key)] = (float(size.get("width") or 0), float(size.get("height") or 0))
        except Exception:
            continue
    pages = {p: {"page": p, "width": w, "height": h, "blocks": [], "pictures": [], "drawings": [], "vector_regions": [], "tables": []}
             for p, (w, h) in page_sizes.items()}
    for item in raw.get("texts") or []:
        prov = (item.get("prov") or [{}])[0]
        try:
            pno = int(prov.get("page_no") or 0)
        except Exception:
            continue
        if pno not in pages:
            continue
        text = str(item.get("text") or item.get("orig") or "").strip()
        if not text:
            continue
        h = pages[pno]["height"]
        pages[pno]["blocks"].append({
            "kind": "heading" if str(item.get("label") or "") in ("title", "section_header") else "paragraph",
            "text": text[:4000], "bbox": _bbox(prov, h), "label": item.get("label"),
        })
    for item in raw.get("pictures") or []:
        prov = (item.get("prov") or [{}])[0]
        try:
            pno = int(prov.get("page_no") or 0)
        except Exception:
            continue
        if pno not in pages:
            continue
        pages[pno]["pictures"].append({
            "kind": "picture", "bbox": _bbox(prov, pages[pno]["height"]),
            "captions": item.get("captions") or [],
        })
    md = doc.export_to_markdown()
    table_blocks = [block.strip() for block in _TABLE_BLOCK.findall(md)]
    for i, item in enumerate(raw.get("tables") or []):
        prov = (item.get("prov") or [{}])[0]
        try:
            pno = int(prov.get("page_no") or 0)
        except Exception:
            continue
        if pno not in pages or i >= len(table_blocks):
            continue
        pages[pno]["tables"].append({
            "kind": "table", "bbox": _bbox(prov, pages[pno]["height"]),
            "text": table_blocks[i][:1600],
        })
    data = {"version": 1, "provider": "docling", "page_count": len(pages),
            "pages": [pages[p] for p in sorted(pages)]}
    (out / "structure.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "docling.md").write_text(md, encoding="utf-8")
    return data
