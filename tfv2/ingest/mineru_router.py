"""MinerU markdown -> PageLedger and per-page routing with Docling."""
from __future__ import annotations

import re
from pathlib import Path

from tfv2.domain.page import Page, PageLedger, PageQuality, PageImage

_PAGE = re.compile(r"<!-- page (\d+) of (\d+) -->")
_IMG = re.compile(r"!\[Image block\]\(([^)]+)\)")
_FORMULA = re.compile(r"!\[Formula block\]\(([^)]+)\)")


def mineru_ledger(markdown: str, *, material: str = "mineru") -> PageLedger:
    parts = _PAGE.split(markdown or "")
    pages: list[Page] = []
    # split -> [before, page, total, body, page, total, body...]
    i = 1
    while i + 2 < len(parts):
        no = int(parts[i]); body = parts[i + 2]
        images = [PageImage(image_id=f"m{no}-img{j}", kind="content", asset_path=u)
                  for j, u in enumerate(_IMG.findall(body), 1)]
        text = _IMG.sub("", body)
        text = _FORMULA.sub("", text)
        pages.append(Page(material=material, page_no=no, text=text.strip(),
                          quality=PageQuality.OCR, images=images,
                          formula_damage=bool(_FORMULA.search(body))))
        i += 3
    return PageLedger(material=material, page_count=len(pages), source_hash="mineru",
                      parser_version="mineru", pages=pages)


def route_pages(docling: PageLedger, mineru: PageLedger) -> PageLedger:
    """Keep Docling text; add MinerU formula/figure assets per page (union, no text loss)."""
    by_m = {p.page_no: p for p in mineru.pages}
    out: list[Page] = []
    for d in docling.pages:
        m = by_m.get(d.page_no)
        images = list(d.images)
        if m:
            images.extend(PageImage(
                image_id=f"mineru-{m.page_no}-{i}", kind="formula",
                asset_path=img.asset_path, bbox=img.bbox)
                for i, img in enumerate(m.images, 1))
        out.append(Page(
            material=docling.material, page_no=d.page_no, text=d.text,
            quality=d.quality, images=images, ocr_used=d.ocr_used,
            formula_damage=d.formula_damage or bool(m and m.formula_damage),
            missing_reason=d.missing_reason))
    return PageLedger(material=docling.material, page_count=docling.page_count,
                      source_hash=f"{docling.source_hash}+mineru-formula",
                      parser_version="router-v2", pages=out)
