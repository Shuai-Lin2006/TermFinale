"""Cloud OCR fallback for image-only pages (Qwen-VL via DashScope).

MinerU is optional and not bundled in the Windows build; when it is missing,
scan/image pages used to stay blank and the lecture degraded to page images.
This module renders empty pages and asks the vision model to transcribe them.
"""
from __future__ import annotations

import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def ocr_empty_pages(pdf: Path, empty_pages: list[int], *, dpi: int = 150, limit: int = 40,
                    progress=None) -> dict[int, str]:
    """OCR the given 1-based page numbers; returns {page: text}."""
    import pymupdf
    from core.ai_vision import ocr_page_text

    pages = [p for p in sorted(set(int(x) for x in empty_pages)) if 1 <= p <= limit]
    if not pages:
        return {}
    out: dict[int, str] = {}
    doc = pymupdf.open(str(pdf))
    try:
        tmp = Path(tempfile.mkdtemp(prefix="tf_cloud_ocr_"))
        images: list[tuple[int, Path]] = []
        for p in pages:
            if p > doc.page_count:
                continue
            pix = doc[p - 1].get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
            img = tmp / f"p{p}.png"
            pix.save(str(img))
            images.append((p, img))
        total = max(1, len(images))
        done = 0
        def work(item):
            p, img = item
            text = ocr_page_text(str(img))
            if text:
                try:
                    from tfv2.render.docx import _latex_to_text
                    text = _latex_to_text(text)
                except Exception:
                    pass
            return p, text
        with ThreadPoolExecutor(max_workers=3) as ex:
            for p, text in ex.map(work, images):
                done += 1
                if text:
                    out[p] = text
                if progress:
                    try:
                        progress(10 + int(30 * done / total), f"Qwen-VL 正在识别第 {done}/{total} 页")
                    except Exception:
                        pass
    finally:
        doc.close()
    return out


def patch_source_pages(src: Path, texts: dict[int, str]) -> int:
    cache = src / "source_pages.json"
    if not cache.is_file() or not texts:
        return 0
    raw = json.loads(cache.read_text(encoding="utf-8"))
    rows = raw.get("pages") if isinstance(raw, dict) else raw
    filled = 0
    for p, text in texts.items():
        idx = p - 1
        if 0 <= idx < len(rows) and text and not str(rows[idx].get("text") or "").strip():
            rows[idx]["text"] = text
            rows[idx]["text_source"] = "qwen-vl"
            rows[idx]["ocr_used"] = True
            filled += 1
    if isinstance(raw, dict):
        raw["pages"] = rows
        cache.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        cache.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return filled
