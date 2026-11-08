"""图文配对审计：图片是否来自资料页、图注是否有效、文件是否可读。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

IMAGE_TAG_RE = re.compile(
    r"\[\[\[IMAGE:\s*(?P<file>[^|\]]+?)\s*\|\s*图注:\s*(?P<cap>.*?)（第\s*(?P<page>\d+)\s*页）\s*\]\]\]",
    re.S,
)
PAGE_RE = re.compile(r"》\s*第\s*(\d+)\s*页】")


@dataclass
class ImageIssue:
    file: str
    page: int
    reason: str


@dataclass
class ImagePairReport:
    total: int = 0
    paired: int = 0
    rate: float = 0.0
    issues: list[ImageIssue] = field(default_factory=list)


def _page_map(pages: list[str]) -> dict[int, str]:
    out = {}
    for b in pages or []:
        m = PAGE_RE.search(b or "")
        if m:
            out[int(m.group(1))] = b
    return out


def audit_images(markdown: str, source_pages: list[str], assets_dir: str | Path) -> ImagePairReport:
    pm = _page_map(source_pages)
    root = Path(assets_dir)
    report = ImagePairReport()
    seen = set()
    for m in IMAGE_TAG_RE.finditer(markdown or ""):
        report.total += 1
        fname = m.group("file").strip()
        cap = re.sub(r"\s+", " ", m.group("cap") or "").strip()
        page = int(m.group("page"))
        key = (fname, page)
        if key in seen:
            continue
        seen.add(key)
        if not fname or not (root / fname).is_file():
            report.issues.append(ImageIssue(fname, page, "图片文件不存在"))
            continue
        if page not in pm:
            report.issues.append(ImageIssue(fname, page, "页码不在资料中"))
            continue
        if fname not in pm[page]:
            report.issues.append(ImageIssue(fname, page, "该页没有对应图片"))
            continue
        if len(cap) < 4 or cap in ("图片", "图示", "无图注"):
            report.issues.append(ImageIssue(fname, page, "图注缺失/过短"))
            continue
        try:
            from PIL import Image
            with Image.open(root / fname) as im:
                w, h = im.size
            if w < 160 or h < 120:
                report.issues.append(ImageIssue(fname, page, f"尺寸过小 {w}x{h}"))
                continue
        except Exception as exc:  # noqa: BLE001
            report.issues.append(ImageIssue(fname, page, f"图片不可读: {type(exc).__name__}"))
            continue
        report.paired += 1
    report.rate = round(report.paired / report.total, 4) if report.total else 1.0
    return report
