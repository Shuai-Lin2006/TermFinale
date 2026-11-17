"""PDF/目录硬门禁：空白页、raw LaTeX、乱码、目录占位标题。"""
from __future__ import annotations
import re
from pathlib import Path

RAW = re.compile(r"\\(?:frac|text|mathrm|begin|end|alpha|beta|gamma|mu|Omega|times|le|ge|sum|int)\b|\$[^$\n]{1,80}\$")
GENERIC = re.compile(r"^第[一二三四五六七八九十百0-9]+节 正文")


def validate_pdf(path: str | Path, sections: list | None = None) -> list[str]:
    p = Path(path)
    issues: list[str] = []
    if not p.is_file() or p.stat().st_size < 1000:
        return ["PDF 不存在或过小"]
    import pymupdf
    doc = pymupdf.open(p)
    try:
        if len(doc) == 0:
            issues.append("PDF 0 页")
        blank = [i + 1 for i, page in enumerate(doc) if len(page.get_text().strip()) < 10]
        if blank:
            issues.append(f"空白页：{blank}")
        text = "\n".join(page.get_text() for page in doc)
        if RAW.search(text):
            m = RAW.search(text)
            issues.append(f"PDF 含未渲染 LaTeX：{m.group(0)[:40]}")
        if "\ufffd" in text or "锟斤拷" in text:
            issues.append("PDF 含替换符/乱码")
    finally:
        doc.close()
    if sections is not None:
        titles = [str(getattr(s, "title", "") or "") for s in sections]
        if titles:
            generic = [t for t in titles if GENERIC.match(t)]
            if generic:
                issues.append(f"目录仍有占位标题：{generic[:3]}")
            if len(titles) > 1 and len(set(titles)) != len(titles):
                issues.append("目录标题重复")
    return issues
