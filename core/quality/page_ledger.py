"""逐页账本：把“页数”与“内容是否真的可用”分开记录。

每页至少标明：页号、文本长度、图片数、是否 OCR 占位、是否被生成物引用。
它不负责生成内容，只负责让“覆盖率”可审计，避免 ok_chunks/chunks 或页头数量冒充内容完整。
"""
from __future__ import annotations

import re
from typing import Iterable

PAGE_HEADER_RE = re.compile(r"》\s*第\s*(\d+)\s*页】")
IMAGE_TAG_RE = re.compile(r"\[\[\[IMAGE:.*?\]\]\]", re.S)
AD_LINE_RE = re.compile(r"(?:QQ\s*群|公众号|蜂考|扫码|关注)")
OCR_MARKERS = ("OCR 未识别", "OCR 未执行", "OCR 失败", "本页为封面", "无文字")

TEXT_OK = 20      # 低于这个长度基本不是可读正文
TEXT_SHORT = 40


def _page_no(block: str, fallback: int) -> int:
    m = PAGE_HEADER_RE.search(block or "")
    return int(m.group(1)) if m else fallback


def _clean_body(block: str) -> str:
    body = PAGE_HEADER_RE.sub("", block or "")
    body = IMAGE_TAG_RE.sub("", body)
    lines = [ln.strip() for ln in body.splitlines()]
    lines = [ln for ln in lines if ln and not AD_LINE_RE.search(ln)]
    return "\n".join(lines).strip()


def build_page_ledger(pages: Iterable[str], markdown: str, total: int | None = None) -> dict:
    pages = list(pages or [])
    if total is None:
        total = len(pages)
    cited = {int(n) for n in re.findall(r"第\s*(\d+)\s*页", markdown or "")}
    detail = []
    for i, block in enumerate(pages, 1):
        n = _page_no(block, i)
        text = _clean_body(block)
        images = len(IMAGE_TAG_RE.findall(block or ""))
        placeholder = any(k in (block or "") for k in OCR_MARKERS)
        if placeholder:
            status = "placeholder"
        elif images and len(text) < TEXT_OK:
            status = "image_only"
        elif len(text) < TEXT_OK:
            status = "short"
        elif n not in cited:
            status = "uncited"
        else:
            status = "cited"
        detail.append({
            "page": n, "chars": len(text), "images": images,
            "placeholder": placeholder, "cited": n in cited, "status": status,
        })
    seen = {x["page"] for x in detail}
    missing = sorted(set(range(1, total + 1)) - seen)
    uncited = [x["page"] for x in detail if not x["cited"]]
    return {
        "pages": total,
        "accounted": len(detail),
        "cited": len([x for x in detail if x["cited"]]),
        "missing_entries": missing,
        "uncited": uncited,
        "placeholder": [x["page"] for x in detail if x["placeholder"]],
        "image_only": [x["page"] for x in detail if x["status"] == "image_only"],
        "short": [x["page"] for x in detail if x["status"] == "short"],
        "status_counts": {k: sum(1 for x in detail if x["status"] == k)
                          for k in ("cited", "uncited", "short", "image_only", "placeholder")},
        "detail": detail,
    }


def ledger_summary(ledger: dict) -> dict:
    return {k: v for k, v in ledger.items() if k != "detail"}
