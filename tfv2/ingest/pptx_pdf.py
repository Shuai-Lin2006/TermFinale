"""PPTX -> PDF fallback when LibreOffice is unavailable.

Normal course PPTs are usually .pptx with text boxes.  Without soffice the
Windows build refused them entirely.  This renderer lays out each slide's
pictures and text on a PDF page so parsing, previews and page references keep
working; it is not a pixel-perfect PowerPoint renderer.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Emu

EMU_PER_PT = 12700.0


def _pt(v) -> float:
    try:
        return float(Emu(v).pt)
    except Exception:
        return 0.0


def _text_of(shape) -> str:
    parts: list[str] = []
    if getattr(shape, "has_text_frame", False):
        for para in shape.text_frame.paragraphs:
            text = "".join(run.text for run in para.runs).strip() or para.text.strip()
            if text:
                parts.append(text)
    if getattr(shape, "has_table", False):
        for row in shape.table.rows:
            cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _iter(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _iter(shape.shapes)


def pptx_to_pdf(source: Path, out_dir: Path) -> Path:
    prs = Presentation(str(source))
    width = _pt(prs.slide_width) or 720.0
    height = _pt(prs.slide_height) or 540.0
    doc = pymupdf.open()
    for slide in prs.slides:
        page = doc.new_page(width=width, height=height)
        for shape in _iter(slide.shapes):
            rect = pymupdf.Rect(_pt(shape.left), _pt(shape.top),
                                _pt(shape.left) + _pt(shape.width),
                                _pt(shape.top) + _pt(shape.height))
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    blob = shape.image.blob
                    if blob:
                        page.insert_image(rect, stream=blob, keep_proportion=True)
                        continue
                except Exception:
                    pass
            text = _text_of(shape)
            if text:
                size = max(9.0, min(22.0, rect.height / max(1.0, len(text.splitlines())) * 0.55))
                try:
                    page.insert_textbox(rect, text, fontsize=size, fontname="china-s",
                                        color=(0.08, 0.10, 0.13), align=0)
                except Exception:
                    pass
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{source.stem}.pdf"
    doc.save(str(target))
    doc.close()
    return target
