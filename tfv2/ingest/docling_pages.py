"""Docling structure -> internal PageLedger/source_pages plugin."""
from __future__ import annotations

import json
from pathlib import Path

from tfv2.domain.page import Page, PageImage, PageLedger, PageQuality


def pages_from_structure(data: dict, *, material: str = "docling") -> PageLedger:
    pages = []
    for raw in data.get("pages") or []:
        no = int(raw.get("page") or len(pages) + 1)
        blocks = raw.get("blocks") or []
        text = "\n".join(str(b.get("text") or "").strip() for b in blocks if str(b.get("text") or "").strip())
        images = []
        for i, pic in enumerate(raw.get("pictures") or [], start=1):
            images.append(PageImage(
                image_id=f"docling_p{no}_{i}",
                kind="content",
                bbox=pic.get("bbox"),
                caption=None,
                asset_path=None,
            ))
        pages.append(Page(material=material, page_no=no, text=text,
                          quality=PageQuality.OCR, images=images, ocr_used=True))
    return PageLedger(material=material, page_count=len(pages),
                      source_hash="docling", parser_version="docling",
                      pages=sorted(pages, key=lambda p: p.page_no))


def save_pages(ledger: PageLedger, path: str | Path) -> Path:
    out = Path(path)
    out.write_text(json.dumps({
        "version": 1, "material": ledger.material, "page_count": ledger.page_count,
        "pages": [p.model_dump(mode="json") for p in ledger.pages],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
