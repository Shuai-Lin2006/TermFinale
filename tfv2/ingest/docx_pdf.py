"""DOCX -> PDF fallback when LibreOffice is unavailable.

Renders paragraphs and table rows into a simple A4 PDF.  Style fidelity is
limited; text, order and page references are preserved for lecture authoring.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf
from docx import Document


def _lines(doc: Document) -> list[str]:
    out: list[str] = []
    for para in doc.paragraphs:
        text = (para.text or "").strip()
        if text:
            out.append(text)
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if cells:
                out.append(" | ".join(cells))
    return out


def docx_to_pdf(source: Path, out_dir: Path) -> Path:
    doc = Document(str(source))
    lines = _lines(doc)
    if not lines:
        raise ValueError("DOCX 中没有可读文字")
    page_w, page_h = 595.0, 842.0          # A4 points
    margin = 56.0
    line_h = 17.0
    per_page = int((page_h - 2 * margin) / line_h)
    pdf = pymupdf.open()
    for start in range(0, len(lines), per_page):
        page = pdf.new_page(width=page_w, height=page_h)
        y = margin
        for text in lines[start:start + per_page]:
            # Wrap long lines by character count (CJK friendly).
            chunk = text
            while chunk:
                part, chunk = chunk[:48], chunk[48:]
                page.insert_text((margin, y), part, fontsize=10.5, fontname="china-s",
                                 color=(0.06, 0.08, 0.10))
                y += line_h
                if y > page_h - margin:
                    break
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{source.stem}.pdf"
    pdf.save(str(target)); pdf.close()
    return target
