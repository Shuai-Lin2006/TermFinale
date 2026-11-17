"""扫描件的公式 OCR：MinerU MFD 检测 + pix2tex 转 LaTeX（本地、离线）。

为什么要单独一层：MinerU 的 flash 档只给纯文本，公式页因此“看得见、搜不到”。
这里把公式区域裁出来交给 pix2tex，得到可渲染的 LaTeX；拿不到就返回空，
**绝不编公式**。公式能不能进 PDF 由 `authoring.normalize._formula_problem` 再校验。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _python() -> str:
    candidates = [
        os.getenv("TERMFINALE_FORMULA_PYTHON", "").strip(),
        str(Path.home() / "Library/Application Support/TermFinale/docling/venv/bin/python"),
        "/private/tmp/docling_venv/bin/python",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return ""


def available() -> bool:
    return bool(_python()) and (ROOT / "tools" / "formula_detect.py").is_file() \
        and (ROOT / "tools" / "formula_ocr.py").is_file()


def latex_ok(latex: str) -> bool:
    """pix2tex 在脏区域会“编公式”，这里挡掉明显的幻觉与 KaTeX 渲染不了的。"""
    body = str(latex or "").strip()
    if not body or len(body) > 220:
        return False
    bad = ("\\Big", "\\stackrel", "\\bigotimes", "\\begin{array}", "\\text{ }", "\\!")
    if any(x in body for x in bad):
        return False
    from tfv2.authoring.normalize import _formula_problem

    return not _formula_problem(body)


def ocr_pdf_formulas(pdf: str | Path, work_dir: str | Path, *, dpi: int = 150,
                     max_pages: int = 12, timeout: int = 240) -> dict[int, list[str]]:
    """返回 {页码: [latex, ...]}；环境不支持/模型不可用时返回空字典。"""
    exe = _python()
    if not exe or not Path(pdf).is_file():
        return {}
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    try:
        import pymupdf
        from PIL import Image
    except Exception:
        return {}
    doc = pymupdf.open(str(pdf))
    renders: list[tuple[int, str]] = []
    try:
        for idx, page in enumerate(doc, start=1):
            if idx > max_pages:
                break
            text = page.get_text("text") or ""
            try:
                pix = page.get_pixmap(dpi=dpi)
            except Exception:
                continue
            path = work / f"mfd_page_{idx:03d}.png"
            pix.save(str(path))
            renders.append((idx, str(path)))
    finally:
        doc.close()
    if not renders:
        return {}
    try:
        proc = subprocess.run([exe, str(ROOT / "tools" / "formula_detect.py"),
                               *[p for _, p in renders]],
                              capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            return {}
        detected = json.loads(proc.stdout or "{}")
    except Exception:
        return {}
    crops: list[tuple[int, str]] = []
    for item in detected.get("images") or []:
        src = Path(str(item.get("path") or ""))
        try:
            page_no = int(src.stem.rsplit("_", 1)[-1])
        except Exception:
            continue
        try:
            with Image.open(src) as im:
                width, height = im.size
        except Exception:
            continue
        for n, box in enumerate(item.get("boxes") or [], start=1):
            cls = str(box.get("cls") or "")
            conf = float(box.get("conf") or 0)
            if conf < (0.40 if cls == "isolated" else 0.70):
                continue
            try:
                x0, y0, x1, y1 = [float(v) for v in box["xyxy"]]
            except Exception:
                continue
            pad = 6
            crop = (max(0, int(x0) - pad), max(0, int(y0) - pad),
                    min(width, int(x1) + pad), min(height, int(y1) + pad))
            if crop[2] - crop[0] < 24 or crop[3] - crop[1] < 14:
                continue
            out = work / f"formula_{page_no:03d}_{n}.png"
            try:
                with Image.open(src) as im:
                    im.crop(crop).save(out)
            except Exception:
                continue
            crops.append((page_no, str(out)))
    if not crops:
        return {}
    try:
        proc = subprocess.run([exe, str(ROOT / "tools" / "formula_ocr.py"), *[p for _, p in crops]],
                              capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            return {}
        items = json.loads(proc.stdout or "{}").get("items") or []
    except Exception:
        return {}
    out: dict[int, list[str]] = {}
    for (page_no, path), item in zip(crops, items):
        latex = re.sub(r"\s+", " ", str(item.get("latex") or "")).replace("\\textstyle", "").strip()
        if not latex_ok(latex):
            continue
        bucket = out.setdefault(page_no, [])
        if latex not in bucket:
            bucket.append(latex)
    return out
