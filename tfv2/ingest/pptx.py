"""PPTX -> v2 PageLedger.

只做页账本，不生成内容；图片可选抽到本地 asset 目录，供后续配图使用。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from tfv2.domain.page import Page, PageImage, PageLedger, PageQuality
from tfv2.ingest.text import sanitize_text

PARSER_VERSION = "tfv2-pptx-0.1"
_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
_NUMBER_RE = re.compile(r"^\s*\d{1,3}\s*$")


def _clean_line(text: str) -> str:
    text = sanitize_text(text).replace("\x0b", " ").replace("\xa0", " ")
    text = re.sub(r"<number>", "", text, flags=re.I)
    text = _DATE_RE.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()
    if _NUMBER_RE.match(text):
        return ""
    return text


def _iter_shapes(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _iter_shapes(shape.shapes)


def _shape_text(shape) -> list[str]:
    out: list[str] = []
    if getattr(shape, "has_text_frame", False):
        for para in shape.text_frame.paragraphs:
            line = _clean_line(para.text)
            if line:
                out.append(line)
    if getattr(shape, "has_table", False):
        for row in shape.table.rows:
            cells = [_clean_line(c.text) for c in row.cells]
            line = " | ".join(x for x in cells if x)
            if line:
                out.append(line)
    return out


def _text_of_slide(slide) -> str:
    parts: list[str] = []
    for shape in _iter_shapes(slide.shapes):
        parts.extend(_shape_text(shape))
    return "\n".join(parts).strip()


def _guess_ext(blob: bytes) -> str:
    if blob.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if blob.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if blob.startswith(b"GIF8"):
        return "gif"
    if blob.startswith(b"RIFF") and blob[8:12] == b"WEBP":
        return "webp"
    return "bin"


def _extract_images(slide, page_no: int, image_dir: Path | None) -> list[PageImage]:
    images: list[PageImage] = []
    idx = 0
    for shape in _iter_shapes(slide.shapes):
        if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
            continue
        idx += 1
        image_id = f"slide_{page_no:03d}_img_{idx}"
        path: Path | None = None
        try:
            blob = shape.image.blob
            try:
                ext = (shape.image.ext or "png").lower()
            except Exception:
                # WMF/EMF 等 PIL 不识别的格式：保留原始字节，渲染阶段再转。
                ext = _guess_ext(blob)
            if image_dir is not None:
                path = image_dir / f"{image_id}.{ext}"
                path.write_bytes(blob)
        except Exception:
            blob = b""
        images.append(
            PageImage(
                image_id=image_id,
                kind="content",
                asset_path=str(path) if path else None,
                discarded_reason=None if path else "无法读取图片字节",
            )
        )
    return images


def build_pptx_page_ledger(
    path: str | Path,
    *,
    material_name: str | None = None,
    image_dir: str | Path | None = None,
) -> PageLedger:
    """把一份 PPTX 读成逐页账本；页数、图片、空页都显式记录。"""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if image_dir is not None:
        image_dir = Path(image_dir)
        image_dir.mkdir(parents=True, exist_ok=True)

    prs = Presentation(str(path))
    pages: list[Page] = []
    for page_no, slide in enumerate(prs.slides, start=1):
        text = _text_of_slide(slide)
        images = _extract_images(slide, page_no, image_dir)
        n_chars = len(re.sub(r"\s+", "", text))
        if n_chars >= 20:
            quality = PageQuality.TEXT
            missing = None
        elif n_chars > 0:
            quality = PageQuality.LOW_TEXT
            missing = None
        elif images:
            quality = PageQuality.IMAGE_ONLY
            missing = "仅图片"
        else:
            quality = PageQuality.EMPTY
            missing = "无文本/图片"
        pages.append(
            Page(
                material=material_name or path.name,
                page_no=page_no,
                text=text,
                quality=quality,
                images=images,
                ocr_used=False,
                formula_damage=False,
                missing_reason=missing,
            )
        )

    return PageLedger(
        material=material_name or path.name,
        page_count=len(pages),
        pages=pages,
        source_hash=hashlib.sha256(path.read_bytes()).hexdigest(),
        parser_version=PARSER_VERSION,
    )
