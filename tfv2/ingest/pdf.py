"""PDF -> v2 PageLedger；只做页账本与图片抽取，不生成内容。"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pymupdf

from tfv2.domain.page import Page, PageImage, PageLedger, PageQuality
from tfv2.ingest.text import sanitize_text

PARSER_VERSION = "tfv2-pdf-0.1"


def _clean(text: str) -> str:
    text = sanitize_text(text).replace("\x00", "").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_images(doc: pymupdf.Document, page: pymupdf.Page, page_no: int,
                    image_dir: Path | None) -> list[PageImage]:
    """Extract only images actually drawn on this page.

    PowerPoint-exported PDFs reuse one global resource dictionary for every
    page. ``page.get_images(full=True)`` then returns every slide asset on
    every page, causing all real diagrams to be deduplicated as repeated
    background. ``get_image_info(xrefs=True)`` reflects the display list.
    """
    out: list[PageImage] = []
    seen_xrefs: set[int] = set()
    try:
        rendered = page.get_image_info(xrefs=True)
    except Exception:
        rendered = []
    for idx, info in enumerate(rendered, start=1):
        xref = int(info.get("xref") or 0)
        if xref <= 0 or xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)
        image_id = f"page_{page_no:03d}_img_{idx}"
        path: Path | None = None
        try:
            data = doc.extract_image(xref)
            ext = (data.get("ext") or "bin").lower()
            blob = data.get("image") or b""
            if image_dir is not None and blob:
                path = image_dir / f"{image_id}.{ext}"
                path.write_bytes(blob)
        except Exception:
            blob = b""
        out.append(PageImage(
            image_id=image_id, kind="content",
            asset_path=str(path) if path else None,
            discarded_reason=None if path else "无法读取图片字节",
        ))
    return out


def build_pdf_page_ledger(
    path: str | Path,
    *,
    material_name: str | None = None,
    image_dir: str | Path | None = None,
) -> PageLedger:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if image_dir is not None:
        image_dir = Path(image_dir)
        image_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(str(path))
    pages: list[Page] = []
    for i, page in enumerate(doc, start=1):
        text = _clean(page.get_text("text"))
        images = _extract_images(doc, page, i, image_dir)
        n = len(re.sub(r"\s+", "", text))
        if n >= 20:
            quality = PageQuality.TEXT; missing = None
        elif n > 0:
            quality = PageQuality.LOW_TEXT; missing = None
        elif images:
            quality = PageQuality.IMAGE_ONLY; missing = "仅图片"
        else:
            quality = PageQuality.EMPTY; missing = "无文本/图片"
        pages.append(Page(
            material=material_name or path.name, page_no=i, text=text,
            quality=quality, images=images, ocr_used=False, formula_damage=False,
            missing_reason=missing,
        ))
    doc.close()
    return PageLedger(
        material=material_name or path.name, page_count=len(pages), pages=pages,
        source_hash="sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        parser_version=PARSER_VERSION,
    )
