"""Save a course's source materials without authoring a lecture.

This is the first step of the course workflow: upload + save. Content tools
can later read the preserved page text; lecture authoring is a separate action.
"""
from __future__ import annotations

import html
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import fitz

from tfv2.product import generate, multi, source_pages
from tfv2.ingest.pdf import build_pdf_page_ledger


def _clean_name(name: str) -> str:
    return Path(str(name or "source.pdf")).name[:120]


def _patch_source_pages_with_ocr(out: Path, ocr_by_file: list[dict]) -> int:
    """把本地 OCR 的页文字补进 source_pages.json；返回补了多少页。"""
    if not any(x.get("pages") for x in ocr_by_file):
        return 0
    cache = out / "source_pages.json"
    if not cache.is_file():
        return 0
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
    except Exception:
        return 0
    rows = data.get("pages") or []
    patched = 0
    for item in ocr_by_file:
        for local_no, text in (item.get("pages") or {}).items():
            idx = int(item["start"]) - 1 + (int(local_no) - 1)
            if idx < 0 or idx >= len(rows):
                continue
            row = rows[idx]
            if str(row.get("text") or "").strip():
                continue
            clean = str(text or "").strip()
            if not clean:
                continue
            row["text"] = clean
            row["text_source"] = "mineru"
            row["ocr_used"] = True
            patched += 1
    if patched:
        data["pages"] = rows
        try:
            cache.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            return 0
    return patched


def _write_headings(out: Path, ocr_by_file: list[dict]) -> None:
    """把 OCR/MinerU 解析出的标题写进 headings.json，供讲义/融合做真实目录。

    页码按合并后的页轴偏移换算；没有标题就不写文件，不制造空目录。
    """
    rows: list[dict] = []
    for item in ocr_by_file:
        offset = int(item.get("start", 1)) - 1
        for h in item.get("headings") or []:
            page = int(h.get("page") or 0)
            text = str(h.get("text") or "").strip()
            if page < 1 or not text:
                continue
            rows.append({"page": offset + page, "level": int(h.get("level") or 1), "text": text})
    if not rows:
        return
    rows.sort(key=lambda x: (x["page"], x["level"]))
    try:
        (out / "headings.json").write_text(json.dumps({"version": 1, "source": "mineru", "headings": rows},
                                                      ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def _write_formulas(out: Path, ocr_by_file: list[dict]) -> None:
    """把 MinerU 解析出的公式写进 formulas.json（页码按合并页轴偏移）。"""
    rows: list[dict] = []
    for item in ocr_by_file:
        offset = int(item.get("start", 1)) - 1
        for f in item.get("formulas") or []:
            page = int(f.get("page") or 0)
            latex = str(f.get("latex") or "").strip()
            if page < 1 or not latex:
                continue
            rows.append({"page": offset + page, "latex": latex, "display": bool(f.get("display"))})
    if not rows:
        return
    rows.sort(key=lambda x: (x["page"], x["display"]))
    try:
        (out / "formulas.json").write_text(
            json.dumps({"version": 1, "source": "mineru", "formulas": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8")
    except Exception:
        return


def save_sources(
    files: list[Path],
    *,
    title: str,
    course: str,
    target_score: int = 80,
    credits: float = 3,
    course_type: str = "",
    school_level: str = "",
    difficulty: int = 3,
    fast: bool = False,
    progress=None,
) -> dict:
    def _prog(pct: int, step: str) -> None:
        if progress:
            try:
                progress(pct, step)
            except Exception:
                pass
    if not files:
        raise ValueError("至少上传一份课程资料")
    if len(files) > 20:
        raise ValueError("一次最多保存 20 份资料")
    # Never use a generic "课程资料" as the course name when the user left it
    # blank. The first file's stem is more useful and keeps courses distinct.
    import re as _re
    _stem = _re.sub(r"^\d+_", "", Path(files[0]).stem)
    title = (title or "").strip() or _stem
    course = (course or "").strip() or title
    aid = generate._new_id()
    out = generate.ARTIFACT_ROOT / aid
    out.mkdir(parents=True, exist_ok=False)
    (out / "source").mkdir()
    (out / "source_pdf").mkdir()

    pdfs: list[Path] = []
    sections: list[dict] = []
    source_meta: list[dict] = []
    ocr_by_file: list[dict] = []
    page_cursor = 0
    section_index = 0
    fast_pending: list[dict] = []
    _prog(8, "准备资料")
    for i, source in enumerate(files, start=1):
        _prog(8 + int(70 * (i - 1) / max(1, len(files))), f"解析第 {i}/{len(files)} 份资料")
        source = Path(source)
        name = _clean_name(source.name)
        target = out / "source" / f"{i:02d}_{name}"
        target.write_bytes(source.read_bytes())
        try:
            pdf = multi._to_pdf(target, out / "source_pdf")
        except Exception as exc:
            raise ValueError(f"{name} 无法读取：{exc}") from exc
        pdfs.append(pdf)
        # 解析后端：文字版 PDF 走快路径，扫描件自动切本地 MinerU（可用 TFV2_PARSE_BACKEND 强制）。
        try:
            if fast:
                # 快速保存：只抽文字层，不做 OCR。扫描件留标记，等生成时再识别。
                from tfv2.ingest.backends import pymupdf_pages
                text_pages = pymupdf_pages(pdf)
                pages = [str(text_pages.get(i + 1) or "").strip() for i in range(len(text_pages))]
                page_count = len(pages)
                parsed = {"pages": text_pages, "headings": [], "formulas": [], "engine": "pymupdf"}
                backend_engine = "pymupdf"
                backend_headings = []
                backend_note = ""
            else:
                from tfv2.ingest.backends import parse_pdf
                parsed = parse_pdf(pdf)
                pages = [str(parsed["pages"].get(i + 1) or "").strip() for i in range(len(parsed["pages"]))]
                page_count = len(pages)
                backend_engine = str(parsed.get("engine") or "")
                backend_headings = list(parsed.get("headings") or [])
                backend_note = str(parsed.get("fallback_reason") or "")
        except Exception as exc:
            raise ValueError(f"{name} 无法解析：{exc}") from exc
        if fast:
            nonempty = sum(1 for x in pages if x.strip())
            if page_count and (nonempty / page_count) < 0.4:
                fast_pending.append({"file": name, "pages": page_count})
        # 扫描件：文字层几乎为空时用本地 MinerU 补文字（0 云端 token），
        # 成功就记下来源，失败也记原因——不让“没解析”变成看不见的空白。
        ocr_engine = backend_engine
        ocr_pages_map: dict[int, str] = {}
        ocr_headings: list[dict] = backend_headings
        ocr_formulas: list[dict] = list(parsed.get("formulas") or [])
        if not ocr_formulas and str(backend_engine).startswith("mineru") \
                and os.getenv("TFV2_FORMULA_OCR", "1").strip() not in ("0", "false", "no"):
            try:
                from tfv2.ingest.formula_ocr import ocr_pdf_formulas
                found = ocr_pdf_formulas(pdf, out / "formula_crops")
                ocr_formulas = [{"page": pno, "latex": latex, "display": True}
                                for pno, items in found.items() for latex in items]
            except Exception:
                ocr_formulas = []
        if backend_engine.startswith("mineru"):
            ocr_pages_map = {i + 1: pages[i] for i in range(page_count) if pages[i]}
        blocks = []
        for pno, text in enumerate(pages, start=1):
            if not text:
                text = "（这一页没有可提取的文字，保留原始 PDF 页）"
            blocks.append({
                "id": f"b{section_index}-{pno}",
                "kind": "paragraph",
                "text": text,
                "source_refs": [{"material": name, "page_start": pno, "page_end": pno}],
            })
        section_index += 1
        sections.append({"id": f"source-{section_index}", "title": Path(name).stem or name, "blocks": blocks})
        source_meta.append({"name": name, "pages": page_count, "pdf": pdf.name,
                            "text_pages": sum(1 for x in pages if x.strip()),
                            "ocr": ocr_engine, "parser": backend_engine,
                            **({"parser_note": backend_note} if backend_note else {})})
        ocr_by_file.append({"start": page_cursor + 1, "count": page_count, "pages": ocr_pages_map,
                            "headings": ocr_headings, "formulas": ocr_formulas})
        page_cursor += page_count

    _prog(82, "合并资料")
    # Merge all source PDFs so the saved course still has a readable/exportable PDF.
    merged = fitz.open()
    for pdf in pdfs:
        part = fitz.open(str(pdf))
        merged.insert_pdf(part)
        part.close()
    lecture_pdf = out / "lecture.pdf"
    merged.save(str(lecture_pdf))
    total_pages = merged.page_count
    merged.close()
    if fast_pending:
        try:
            (out / "ocr_pending.json").write_text(json.dumps(
                {"files": fast_pending, "source_pdf": "lecture.pdf",
                 "note": "快速保存，扫描件 OCR 推迟到生成时"}, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception:
            pass
    _prog(90, "建立页账本")
    try:
        page_ledger = build_pdf_page_ledger(lecture_pdf, material_name=Path(files[0]).name,
                                            image_dir=out / "source_assets")
        source_pages.save_source_pages(out, page_ledger)
    except Exception:
        pass
    # OCR 出来的文字必须写进 source_pages：提取/练习/出卷读的是这份页数据，
    # 只写进 sections 的话，扫描件在模块里仍然等于空白页。
    _patch_source_pages_with_ocr(out, ocr_by_file)
    _write_headings(out, ocr_by_file)
    _write_formulas(out, ocr_by_file)

    # Plain, dependency-free source reader. The parent reader supplies search,
    # export and navigation; this page is intentionally just readable material.
    body = []
    for section in sections:
        body.append(f"<h2>{html.escape(section['title'])}</h2>")
        for block in section["blocks"]:
            page = block["source_refs"][0]["page_start"]
            body.append(f'<section class="raw-page" data-pages="{page}"><div class="raw-page-no">第 {page} 页</div><p>{html.escape(block["text"])}</p></section>')
    lecture_html = """<!doctype html><html><head><meta charset="utf-8"><style>
      body{margin:0;background:#f7f4ec;color:#26332b;font-family:"PingFang SC","Microsoft YaHei",sans-serif}
      .lecture{max-width:920px;margin:0 auto;padding:56px 56px 90px;background:#fffdf8}
      .kicker{font-size:10px;letter-spacing:.22em;color:#7d877d;margin-bottom:12px}
      h1{font-family:"Songti SC","STSong",serif;font-size:34px;margin:0 0 8px;color:#1f3327}
      .meta{font-size:12px;color:#7f887e;margin-bottom:30px}
      h2{font-family:"Songti SC","STSong",serif;font-size:23px;margin:32px 0 12px;border-bottom:1px solid #d9ded4;padding-bottom:8px}
      .raw-page{margin:0 0 22px}.raw-page-no{font:10px monospace;color:#97a095}.raw-page p{white-space:pre-wrap;font-size:15px;line-height:1.95;margin:8px 0}
      @media print{body{background:#fff}.lecture{padding:0;max-width:none}}
    </style></head><body><div class="lecture"><div class="kicker">SAVED COURSE MATERIAL · 资料原文</div><h1>%s</h1><div class="meta">%s · 共 %d 页 · 保存于 %s</div>%s</div></body></html>""" % (
        html.escape(title), html.escape(course), total_pages, datetime.now().strftime("%Y-%m-%d %H:%M"), "".join(body)
    )
    (out / "lecture.html").write_text(lecture_html, encoding="utf-8")
    (out / "sections.json").write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "artifact": title, "chapter": title, "course": course,
        "page_count": total_pages, "pdf_pages": total_pages,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_only": True, "figures": 0,
        "gate": {"passed": True, "issues": []},
        "content_gate": {"issues": []}, "pdf_content_gate": {"issues": []},
        "language": {"issues": []}, "scope_coverage": "saved-source",
        "sources": source_meta,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # key 必须和 service._view 推导出来的一致，否则日志/响应/产物各说各话。
    from tfv2.product.service import course_key_for

    return {"id": aid, "title": title, "course": course, "course_key": course_key_for(course),
            "pages": total_pages, "sources": len(files)}
