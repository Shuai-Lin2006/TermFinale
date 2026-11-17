"""Lightweight source structure model.

This is our local, dependency-free equivalent of the document model used by
Docling/MinerU: every page gets ordered text blocks with bbox, plus picture and
vector-drawing regions with provenance. It is deliberately optional: failure
must not break lecture generation.
"""
from __future__ import annotations

import json
from pathlib import Path


def _bbox(value) -> list[float] | None:
    try:
        if value is None:
            return None
        if hasattr(value, "x0"):
            return [round(float(value.x0), 2), round(float(value.y0), 2),
                    round(float(value.x1), 2), round(float(value.y1), 2)]
        return [round(float(x), 2) for x in value[:4]]
    except Exception:
        return None


def build_source_structure(pdf_path: str | Path, out_dir: str | Path,
                           image_dir: str | Path | None = None) -> dict:
    import pymupdf

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    image_dir = Path(image_dir) if image_dir else None
    if image_dir:
        image_dir.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(str(pdf_path))
    pages: list[dict] = []
    try:
        for page in doc:
            pno = page.number + 1
            pw, ph = float(page.rect.width), float(page.rect.height)
            blocks: list[dict] = []
            try:
                raw = page.get_text("dict")
            except Exception:
                raw = {}
            for b in (raw.get("blocks") or []):
                if b.get("type") != 0:
                    continue
                bbox = _bbox(b.get("bbox"))
                if not bbox:
                    continue
                lines = []
                sizes = []
                for line in b.get("lines") or []:
                    text = "".join(str(s.get("text") or "") for s in (line.get("spans") or []))
                    if text.strip():
                        lines.append(text)
                        sizes += [float(s.get("size") or 0) for s in (line.get("spans") or []) if s.get("size")]
                text = "\n".join(lines).strip()
                if not text:
                    continue
                size = round(max(sizes), 1) if sizes else None
                # Relative font size is a useful heading hint across PDFs/PPT exports.
                kind = "heading" if size and size >= 15 else "paragraph"
                blocks.append({"kind": kind, "text": text, "bbox": bbox, "font_size": size})
            pictures: list[dict] = []
            try:
                for idx, info in enumerate(page.get_image_info(xrefs=True), start=1):
                    bb = _bbox(info.get("bbox"))
                    if not bb:
                        continue
                    pictures.append({"kind": "picture", "bbox": bb, "xref": int(info.get("xref") or 0),
                                     "index": idx})
            except Exception:
                pass
            drawings: list[dict] = []
            try:
                for d in page.get_drawings():
                    bb = _bbox(d.get("rect"))
                    if not bb:
                        continue
                    area = max(0.0, (bb[2] - bb[0]) * (bb[3] - bb[1]))
                    # Full-page backgrounds are not diagrams.
                    if area > pw * ph * 0.72:
                        continue
                    drawings.append({"kind": "drawing", "bbox": bb})
            except Exception:
                pass
            vector_crop = None
            vector_regions: list[dict] = []
            if image_dir and drawings:
                import pymupdf as _fitz
                boxes = [tuple(d["bbox"]) for d in drawings if d["bbox"][2] > d["bbox"][0] and d["bbox"][3] > d["bbox"][1]]
                # Merge nearby shapes into connected regions. A slide with three
                # separate circuit diagrams must produce three crops, not one
                # full-slide screenshot.
                groups: list[list[float]] = []
                for b in boxes:
                    placed = False
                    for g in groups:
                        if not (b[2] < g[0] - 24 or b[0] > g[2] + 24 or b[3] < g[1] - 24 or b[1] > g[3] + 24):
                            g[0] = min(g[0], b[0]); g[1] = min(g[1], b[1])
                            g[2] = max(g[2], b[2]); g[3] = max(g[3], b[3])
                            placed = True
                            break
                    if not placed:
                        groups.append([b[0], b[1], b[2], b[3]])
                # Repeat merge because one union can bridge other clusters.
                changed = True
                while changed:
                    changed = False
                    for i in range(len(groups)):
                        for j in range(i + 1, len(groups)):
                            a, b = groups[i], groups[j]
                            if not (b[2] < a[0] - 24 or b[0] > a[2] + 24 or b[3] < a[1] - 24 or b[1] > a[3] + 24):
                                a[0] = min(a[0], b[0]); a[1] = min(a[1], b[1])
                                a[2] = max(a[2], b[2]); a[3] = max(a[3], b[3])
                                groups.pop(j); changed = True; break
                        if changed:
                            break
                if groups:
                    x0 = max(0.0, min(g[0] for g in groups) - 8)
                    y0 = max(0.0, min(g[1] for g in groups) - 8)
                    x1 = min(pw, max(g[2] for g in groups) + 8)
                    y1 = min(ph, max(g[3] for g in groups) + 8)
                    if (x1 - x0) >= 180 and (y1 - y0) >= 100 and (x1 - x0) * (y1 - y0) < pw * ph * 0.78:
                        try:
                            pix = page.get_pixmap(clip=_fitz.Rect(x0, y0, x1, y1), dpi=150)
                            crop_path = image_dir / f"vector_page_{pno:03d}.png"
                            pix.save(str(crop_path))
                            vector_crop = str(crop_path)
                        except Exception:
                            vector_crop = None
                for gi, g in enumerate(groups[:6], start=1):
                    rx0, ry0 = max(0.0, g[0] - 12), max(0.0, g[1] - 12)
                    rx1, ry1 = min(pw, g[2] + 12), min(ph, g[3] + 12)
                    if (rx1 - rx0) < 120 or (ry1 - ry0) < 70 or (rx1 - rx0) * (ry1 - ry0) > pw * ph * 0.42:
                        continue
                    try:
                        pix = page.get_pixmap(clip=_fitz.Rect(rx0, ry0, rx1, ry1), dpi=150)
                        crop_path = image_dir / f"vector_page_{pno:03d}_region_{gi}.png"
                        pix.save(str(crop_path))
                        vector_regions.append({"bbox": [rx0, ry0, rx1, ry1], "asset_path": str(crop_path)})
                    except Exception:
                        continue
            pages.append({"page": pno, "width": pw, "height": ph,
                          "blocks": blocks, "pictures": pictures, "drawings": drawings[:80],
                          "vector_crop": vector_crop, "vector_regions": vector_regions})
    finally:
        doc.close()
    data = {"version": 1, "page_count": len(pages), "pages": pages}
    (out / "structure.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
