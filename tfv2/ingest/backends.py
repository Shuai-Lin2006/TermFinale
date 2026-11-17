"""解析后端：同一份 PDF，可以选择用 PyMuPDF 文字层还是本地 MinerU 解析。

为什么不直接全换 MinerU：
- 文字版 PDF 用 PyMuPDF 又快又准，没必要上模型；
- 扫描件/公式教材才需要 MinerU；
- “自动”按文字层产出率判断，用户也能通过 TFV2_PARSE_BACKEND 强制指定，
  强制指定失败时必须报原因，不能悄悄换回另一个后端。
"""
from __future__ import annotations

import os
from pathlib import Path

AUTO = "auto"
PYMUPDF = "pymupdf"
MINERU = "mineru"
CHOICES = (AUTO, PYMUPDF, MINERU)

MIN_CHARS_PER_PAGE = 30      # 平均每页低于这个数，基本等于没有文字层
EMPTY_PAGE_RATIO = 0.6       # 六成以上的页没有文字，就判定为扫描件


def configured_backend() -> str:
    raw = os.getenv("TFV2_PARSE_BACKEND", AUTO).strip().lower()
    return raw if raw in CHOICES else AUTO


def pymupdf_pages(pdf: str | Path) -> dict[int, str]:
    import pymupdf

    doc = pymupdf.open(str(pdf))
    try:
        return {i + 1: (page.get_text("text") or "").strip() for i, page in enumerate(doc)}
    finally:
        doc.close()


def parse_pdf(pdf: str | Path, *, backend: str | None = None) -> dict:
    """返回 {"pages": {页码: 文本}, "headings": [...], "engine": "pymupdf"|"mineru-local"}。

    auto：先看 PyMuPDF 的文字产出，低于阈值才上 MinerU（并说明为什么换）。
    """
    name = (backend or configured_backend()).lower()
    if name not in CHOICES:
        raise ValueError(f"未知解析后端：{name}（可选 {CHOICES}）")
    src = Path(pdf)
    if not src.is_file():
        raise FileNotFoundError(f"文件不存在：{src}")

    if name == PYMUPDF:
        return {"pages": pymupdf_pages(src), "headings": [], "formulas": [], "engine": PYMUPDF}

    from tfv2.ingest.mineru_backend import ocr_pdf_document

    if name == MINERU:
        doc = ocr_pdf_document(src)
        return {"pages": doc.get("pages") or {}, "headings": list(doc.get("headings") or []),
                "formulas": list(doc.get("formulas") or []),
                "engine": str(doc.get("engine") or "mineru-local"), "forced": True}

    text_pages = pymupdf_pages(src)
    n = max(1, len(text_pages))
    total = sum(len(v) for v in text_pages.values())
    empty = sum(1 for v in text_pages.values() if len(v.strip()) < 20)
    empty_ratio = empty / n
    if total / n >= MIN_CHARS_PER_PAGE and empty_ratio < EMPTY_PAGE_RATIO:
        return {"pages": text_pages, "headings": [], "formulas": [], "engine": PYMUPDF}
    doc = ocr_pdf_document(src)
    return {"pages": doc.get("pages") or {}, "headings": list(doc.get("headings") or []),
            "formulas": list(doc.get("formulas") or []),
            "engine": str(doc.get("engine") or "mineru-local"),
            "fallback_reason": (f"文字层每页 {total / n:.0f} 字、空白页 {empty_ratio:.0%}，"
                                "判定为扫描件，改用本地 OCR")}
