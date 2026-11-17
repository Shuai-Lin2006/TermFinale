"""资料类型回归：PDF / 扫描件 / 公式教材 / PPTX / DOCX / 图片 全部走同一条页模型。

用法：
  .venv/bin/python scripts/material_types_e2e.py [--keep]

每个类型都验证：
1. 能入库（不直接报错），页数 > 0；
2. 页文本里没有 ￿ / 私用区 / 控制字符（公式页尤其）；
3. 能从这里生成一份小讲义，页数对得上、每页都有出处、无乱码；
4. 扫描/P PT/图片这类没有文字的页，讲义里保留原页影像，不硬转乱码。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCRATCH = Path(tempfile.mkdtemp(prefix="tf_types_e2e_"))
DATA = SCRATCH / "data"
(DATA / "artifacts").mkdir(parents=True, exist_ok=True)
os.environ["TFV2_DATA_ROOT"] = str(DATA)

import pymupdf  # noqa: E402
from PIL import Image  # noqa: E402

from tfv2.product import service  # noqa: E402
from tfv2.product.source_digest import build_source_digest  # noqa: E402
from tfv2.product.sources import save_sources  # noqa: E402

FAILURES: list[str] = []
BAD = ("\ufffd", "\ue000", "锟斤拷", "\uf8ff")
MARKERS = {
    "pdf": "共射放大电路的静态工作点",
    "formula": "lim_{x→0} sin x / x = 1",
    "pptx": "三极管的输入特性曲线",
    "docx": "共基极电流放大系数",
}


def check(cond: bool, msg: str) -> None:
    print(f"  [{'ok' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILURES.append(msg)


def _text_pdf(path: Path, lines: list[str]) -> Path:
    doc = pymupdf.open()
    for i, line in enumerate(lines, start=1):
        page = doc.new_page()
        # 内置简体中文字体，否则中文在 PDF 里会被编码成乱码。
        page.insert_text((60, 80), line, fontsize=13, fontname="china-s", fontfile=None)
        if i == 1:
            page.insert_text((60, 130), "这一页用于资料类型回归。", fontsize=12,
                             fontname="china-s", fontfile=None)
    doc.save(str(path))
    doc.close()
    return path


def _scan_pdf(path: Path, count: int = 2) -> Path:
    doc = pymupdf.open()
    for i in range(count):
        img = SCRATCH / f"scan_{i}.png"
        Image.new("RGB", (600, 800), "white").save(img)
        page = doc.new_page(width=600, height=800)
        page.insert_image(pymupdf.Rect(0, 0, 600, 800), filename=str(img))
    doc.save(str(path))
    doc.close()
    return path


def _pptx(path: Path) -> Path:
    from pptx import Presentation
    pr = Presentation()
    slide = pr.slides.add_slide(pr.slide_layouts[5])
    slide.shapes.title.text = MARKERS["pptx"]
    box = slide.shapes.add_textbox(10, 10, 500, 100)
    box.text_frame.text = "输入特性：UCE 固定时 IB 与 UBE 的关系。"
    slide2 = pr.slides.add_slide(pr.slide_layouts[5])
    slide2.shapes.title.text = "输出特性曲线"
    pr.save(str(path))
    return path


def _docx(path: Path) -> Path:
    from docx import Document
    d = Document()
    d.add_heading(MARKERS["docx"], level=1)
    d.add_paragraph("共基极电流放大系数 α 略小于 1，体现共基极接法下的电流放大作用。")
    d.save(str(path))
    return path


def _image(path: Path) -> Path:
    img = Image.new("RGB", (700, 500), "white")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), "handwritten scan page", fill="black")
    img.save(str(path))
    return path


def build_samples() -> dict[str, Path]:
    return {
        "pdf": _text_pdf(SCRATCH / "lecture.pdf", [MARKERS["pdf"],
                                                   "直流通路与交流通路要分开画，否则静态工作点会算错。"]),
        "scan": _scan_pdf(SCRATCH / "scan.pdf", 3),
        "formula": _text_pdf(SCRATCH / "formula.pdf", ["重要极限", MARKERS["formula"],
                                                       "∫_0^1 x^2 dx = 1/3"]),
        "pptx": _pptx(SCRATCH / "slides.pptx"),
        "docx": _docx(SCRATCH / "notes.docx"),
        "png": _image(SCRATCH / "page.png"),
        "jpg": _image(SCRATCH / "photo.jpg"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    samples = build_samples()
    started = time.time()

    for kind, path in samples.items():
        print(f"\n== {kind}: {path.name} ==")
        try:
            saved = save_sources([path], title=f"{kind} 样张", course="资料类型回归")
        except Exception as exc:  # noqa: BLE001
            check(False, f"{kind} 入库失败：{type(exc).__name__}: {exc}")
            continue
        aids = saved.get("artifacts") or [saved.get("id")]
        aid = aids[0]
        meta = service.get_artifact(aid) or {}
        pages = int(meta.get("page_count") or 0)
        check(pages > 0, f"入库成功，{pages} 页")

        raw = json.loads((service.artifact_path(aid) / "source_pages.json").read_text(encoding="utf-8"))
        rows = raw.get("pages") or []
        all_text = "\n".join(str(r.get("text") or "") for r in rows)
        bad = [c for c in BAD if c in all_text]
        check(not bad, f"页文本无乱码/私用区（命中 {bad}）")

        if kind in MARKERS:
            check(MARKERS[kind] in all_text, f"文本里能找到关键内容「{MARKERS[kind][:12]}…」")
        if kind in ("scan", "png", "jpg"):
            text_pages = [r for r in rows if len(str(r.get("text") or "").strip()) >= 24]
            check(not text_pages, f"扫描/图片没有伪造文字（有文字的页：{len(text_pages)}）")

        # 从这份资料生成一份小讲义
        take = list(range(1, min(3, pages) + 1))
        out_id = f"types-{kind}"
        try:
            build_source_digest(aid, take, out_id, scan_mode=kind in ("scan", "png", "jpg"))
        except Exception as exc:  # noqa: BLE001
            check(False, f"{kind} 生成讲义失败：{type(exc).__name__}: {exc}")
            continue
        dest = service.artifact_path(out_id)
        ok_pdf = dest is not None and (dest / "lecture.pdf").is_file()
        check(ok_pdf, "生成讲义 PDF")
        if not ok_pdf:
            continue
        sections = json.loads((dest / "sections.json").read_text(encoding="utf-8"))
        cited = set()
        for sec in sections:
            for block in sec.get("blocks") or []:
                for ref in block.get("source_refs") or []:
                    cited.update(range(int(ref["page_start"]), int(ref.get("page_end") or ref["page_start"]) + 1))
        check(cited == set(take), f"选中页全部被引用（{sorted(cited)}）")
        html = (dest / "lecture.html").read_text(encoding="utf-8")
        check(not [c for c in BAD if c in html], "讲义 HTML 无乱码")
        figs = [b for sec in sections for b in sec.get("blocks") or [] if b.get("kind") == "figure"]
        if kind in ("scan", "png", "jpg"):
            check(len(figs) == len(take), f"无文字页保留原页影像（{len(figs)}/{len(take)}）")

    print(f"\n总耗时 {time.time() - started:.1f}s")
    if args.keep:
        print(f"产物目录：{DATA / 'artifacts'}")
    if FAILURES:
        print(f"\nFAILED（{len(FAILURES)} 条）：")
        for item in FAILURES:
            print(f" - {item}")
        raise SystemExit(1)
    print("\nALL PASSED")
    if not args.keep:
        shutil.rmtree(SCRATCH, ignore_errors=True)


if __name__ == "__main__":
    main()
