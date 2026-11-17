"""PDF 版面体检：图片比例、出血/越界、页面过密与孤页风险。

这是提示性检查，不直接阻断交付；真正的硬门禁仍在 pdf_gate/content_gate。
"""
from __future__ import annotations

from pathlib import Path


def validate_layout(path: str | Path) -> dict:
    import pymupdf

    issues: list[dict] = []
    doc = pymupdf.open(str(path))
    try:
        for page in doc:
            w, h = page.rect.width, page.rect.height
            if w <= 0 or h <= 0:
                continue
            pno = page.number + 1
            text_blocks = (page.get_text("dict") or {}).get("blocks") or []
            text_height = 0.0
            for block in text_blocks:
                if block.get("type") != 0:
                    continue
                bbox = block.get("bbox") or (0, 0, 0, 0)
                x0, y0, x1, y1 = [float(v) for v in bbox]
                text_height += max(0.0, y1 - y0)
                if x0 < -2 or y0 < -2 or x1 > w + 2 or y1 > h + 2:
                    issues.append({"code": "layout.out_of_bounds", "severity": "hard",
                                   "page": pno, "message": "正文块超出页面边界"})
            for info in page.get_image_info():
                bbox = info.get("bbox") or (0, 0, 0, 0)
                x0, y0, x1, y1 = [float(v) for v in bbox]
                ih, iw = y1 - y0, x1 - x0
                if ih > h * 0.62:
                    issues.append({"code": "layout.figure_too_tall", "severity": "warn",
                                   "page": pno,
                                   "message": f"图片高度占页面 {ih / h:.0%}，可能挤压正文"})
                if iw > w * 0.98 and ih > h * 0.5:
                    issues.append({"code": "layout.figure_too_large", "severity": "warn",
                                   "page": pno,
                                   "message": "图片宽高过大，建议缩放到正文宽度内"})
            # A healthy A4 page can accumulate a lot of block bbox height;
            # only flag genuinely extreme density to avoid noisy false alarms.
            if text_height > h * 1.7:
                issues.append({"code": "layout.page_dense", "severity": "warn",
                               "page": pno, "message": "该页文字密度异常高，建议检查分页"})
    finally:
        doc.close()
    return {"issues": issues, "passed": not any(x["severity"] == "hard" for x in issues)}


def layout_report_markdown(report: dict) -> str:
    lines = ["# 版面体检报告", "", f"- 结果：{'通过' if report.get('passed') else '有硬性版面问题'}",
             f"- 提醒：{len(report.get('issues') or [])} 条", ""]
    for x in report.get("issues") or []:
        lines.append(f"- 第 {x.get('page')} 页：{x.get('message')}（{x.get('code')}）")
    return "\n".join(lines) + "\n"
