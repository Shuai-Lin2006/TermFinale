
"""Immutable source pages for an artifact.

Generated lecture sections are a *teaching layer*. Extraction, exam authoring
and practice must read the original pages, otherwise an "original question"
mode can never find the original wording. This module caches a raw page ledger
next to the artifact so later tasks do not have to parse the source again.
"""
from __future__ import annotations

import json
from pathlib import Path

CACHE_NAME = "source_pages.json"


def _source_candidates(path: Path) -> list[Path]:
    out: list[Path] = []
    for folder, suffixes in (("source", (".pptx", ".pdf")), ("source_pdf", (".pdf",))):
        base = path / folder
        if not base.is_dir():
            continue
        for item in sorted(base.iterdir()):
            if item.is_file() and item.suffix.lower() in suffixes:
                out.append(item)
    # PPTX has the cleanest text/image ledger; use it before a converted PDF.
    out.sort(key=lambda p: (0 if p.suffix.lower() == ".pptx" else 1, str(p)))
    return out


def _ledger_for(candidate: Path, image_dir: Path):
    suffix = candidate.suffix.lower()
    if suffix == ".pdf":
        from tfv2.ingest.pdf import build_pdf_page_ledger
        return build_pdf_page_ledger(candidate, material_name=candidate.name, image_dir=image_dir)
    if suffix == ".pptx":
        from tfv2.ingest.pptx import build_pptx_page_ledger
        return build_pptx_page_ledger(candidate, material_name=candidate.name, image_dir=image_dir)
    return None


def save_source_pages(path: Path, ledger) -> None:
    path = Path(path)
    data = []
    for page in ledger.pages:
        data.append({
            "page": page.page_no,
            "source_page": page.page_no,
            "text": page.text or "",
            "quality": page.quality.value if hasattr(page.quality, "value") else str(page.quality),
            "images": [
                {
                    "image_id": img.image_id,
                    "asset_path": img.asset_path,
                    "caption": img.caption,
                    "kind": img.kind,
                    "bbox": img.bbox,
                }
                for img in page.images
            ],
        })
    (path / CACHE_NAME).write_text(json.dumps({
        "version": 1,
        "material": ledger.material,
        "page_count": ledger.page_count,
        "pages": data,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def load_source_pages(path: Path, *, refresh: bool = False) -> list[dict] | None:
    path = Path(path)
    cache = path / CACHE_NAME
    if cache.is_file() and not refresh:
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            pages = data.get("pages") if isinstance(data, dict) else None
            if isinstance(pages, list) and pages and all(isinstance(x, dict) and x.get("page") for x in pages):
                return pages
        except Exception:
            pass
    for candidate in _source_candidates(path):
        try:
            ledger = _ledger_for(candidate, path / "source_assets")
            save_source_pages(path, ledger)
            return load_source_pages(path)
        except Exception:
            continue
    return None


def page_map(pages: list[dict]) -> dict[int, str]:
    out: dict[int, str] = {}
    for page in pages or []:
        try:
            out[int(page.get("page"))] = str(page.get("text") or "")
        except Exception:
            continue
    return out


def source_context(pages: list[dict], page_numbers: list[int] | None = None, limit: int = 9000) -> str:
    wanted = set(int(x) for x in (page_numbers or []))
    parts: list[str] = []
    for page in pages or []:
        try:
            no = int(page.get("page"))
        except Exception:
            continue
        if wanted and no not in wanted:
            continue
        text = str(page.get("text") or "").strip()
        if not text:
            text = "（本页无文字，仅有图片/图示）"
        parts.append(f"【第 {no} 页】\n{text}")
    return "\n\n".join(parts)[:limit]


def source_stats(pages: list[dict]) -> dict:
    if not pages:
        return {"pages": 0, "text_pages": 0, "image_only_pages": 0, "empty_pages": 0}
    text_pages = sum(1 for p in pages if len(str(p.get("text") or "").strip()) >= 20)
    image_only = sum(1 for p in pages if not str(p.get("text") or "").strip() and p.get("images"))
    return {
        "pages": len(pages),
        "text_pages": text_pages,
        "image_only_pages": image_only,
        "empty_pages": len(pages) - text_pages - image_only,
    }
