"""Generate a 2-page preview artifact for a job, without running the whole book."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pymupdf

from core import paths
from tfv2.authoring.lecture import author_section
from tfv2.authoring.normalize import normalize_section, sanitize_math
from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef
from tfv2.domain.page import Page, PageLedger, PageQuality
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.fact_map import facts_for_pages, map_facts
from tfv2.authoring.page_facts import extract_page_facts
from tfv2.build import build_project


def _mark_preview(dir_path: Path) -> None:
    """预览不进入“我的课程/讲义库”，只作为试看产物。"""
    manifest = dir_path / "manifest.json"
    if not manifest.is_file():
        return
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["preview"] = True
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _ensure_ocr(src: Path, progress=None, page_numbers: list[int] | None = None) -> None:
    """快速保存留下的 OCR 欠账：第一次生成时补识别，再写回页数据。

    先试本地 MinerU；它不可用（Windows 默认没装）或识别不到时，用云 OCR
    （DashScope Qwen-VL）补齐空页。任何一步失败都不阻断生成。
    """
    marker = src / "ocr_pending.json"
    if not marker.is_file():
        return
    filled = 0
    selected = sorted({int(p) for p in (page_numbers or []) if int(p) > 0})
    # 选页生成时绝不能跑整本 MinerU/整本 OCR：273 页的教材会把 10 页预览拖到十几分钟。
    # 只有全量调用（没有选页）才尝试本地 MinerU。
    if not selected:
        try:
            from tfv2.ingest.backends import parse_pdf
            if progress:
                progress(4, "识别扫描件（首次生成）")
            parsed = parse_pdf(src / "lecture.pdf", backend="mineru")
            raw = json.loads((src / "source_pages.json").read_text(encoding="utf-8"))
            rows = raw.get("pages") or raw
            for i, row in enumerate(rows):
                text = str(parsed["pages"].get(i + 1) or "").strip()
                if text and not str(row.get("text") or "").strip():
                    row["text"] = text
                    row["ocr_used"] = True
                    filled += 1
            if isinstance(raw, dict):
                raw["pages"] = rows
            (src / "source_pages.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # 本地 OCR 不可用/没补全：云 OCR 兜底
    try:
        from tfv2.product import cloud_ocr
        raw2 = json.loads((src / "source_pages.json").read_text(encoding="utf-8"))
        rows2 = raw2.get("pages") if isinstance(raw2, dict) else raw2
        def _bad(text: str) -> bool:
            t = str(text or "").strip()
            if len(t) < 30:
                return True
            bad = sum(1 for ch in t if 0xE000 <= ord(ch) <= 0xF8FF or ch in "\ufffc\ufffd")
            return bad / max(1, len(t)) > 0.01
        if selected:
            empty = [p for p in selected if 1 <= p <= len(rows2) and _bad(rows2[p - 1].get("text"))]
        else:
            empty = [i + 1 for i, row in enumerate(rows2) if _bad(row.get("text"))][:16]
        pdfs = [src / "lecture.pdf"] + list((src / "source_pdf").glob("*.pdf")) + list((src / "source").glob("*.pdf"))
        pdf = next((x for x in pdfs if x.is_file()), None)
        if empty and pdf is not None:
            if progress:
                progress(10, f"云 OCR 补齐 {len(empty)} 页")
            texts = cloud_ocr.ocr_empty_pages(pdf, empty, progress=progress)
            filled += cloud_ocr.patch_source_pages(src, texts)
    except Exception:
        pass
    marker.unlink(missing_ok=True)
    if progress:
        progress(10, f"扫描件识别完成（补了 {filled} 页）")


def generate_preview(artifact_id: str, job_id: str, *, pages: int = 2, page_numbers: list[int] | None = None,
                     persona: str = "老师", custom_prompt: str = "", progress=None) -> Path:
    from tfv2.product import service
    src = service.artifact_path(artifact_id)
    if src is None:
        raise FileNotFoundError("artifact not found")
    _ensure_ocr(src, progress, page_numbers or list(range(1, max(1, pages) + 1)))
    raw = json.loads((src / "source_pages.json").read_text(encoding="utf-8"))
    all_rows = raw.get("pages") or raw
    # 扫描件/文字层可能把 LaTeX 命令原样带进来；生成前降级成可读文本。
    try:
        from tfv2.render.docx import _latex_to_text
        for row in all_rows:
            t = str(row.get("text") or "")
            if "\\" in t or "$" in t:
                row["text"] = _latex_to_text(t)
    except Exception:
        pass
    if page_numbers:
        chosen = sorted({int(p) for p in page_numbers if 1 <= int(p) <= len(all_rows)})[:16]
        if not chosen:
            raise ValueError("没有有效页码")
        indices = [p - 1 for p in chosen]
        rows = [dict(all_rows[i], page=j + 1) for j, i in enumerate(indices)]
    else:
        rows = [dict(x, page=i + 1) for i, x in enumerate(all_rows[:max(1, min(pages, len(all_rows)))])]
        indices = list(range(len(rows)))
    sections: list = []
    chunk_size = 8 if len(rows) > 10 else (6 if len(rows) > 8 else (4 if len(rows) > 4 else 2))
    chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    progress_lock = threading.Lock()

    def _progress(pct: int, step: str) -> None:
        if not progress:
            return
        with progress_lock:
            try:
                progress(pct, step)
            except Exception:
                pass

    def _build(ci: int, chunk: list, offset: int):
        local_texts = {j + 1: (row.get("text") or "") for j, row in enumerate(chunk)}
        local_ledger = PageLedger(
            material=artifact_id, page_count=len(chunk), source_hash="preview",
            parser_version="preview",
            pages=[Page(material=artifact_id, page_no=j, text=local_texts[j], quality=PageQuality.OCR)
                   for j in local_texts],
        )
        local_facts = facts_for_pages(local_texts, list(local_texts), per_page=8)
        _progress(12 + int(40 * (ci - 1) / max(1, len(chunks))), f"第 {ci}/{len(chunks)} 单元：规划")
        def _author(author_client):
            return author_section(
                author_client, local_ledger, chapter_title="预览",
                section_title=f"第 {offset + 1}–{offset + len(chunk)} 页",
                pages=list(local_texts), target_score=80, days_left=7,
                foundation="基础较弱", persona=(persona or "老师"), gen_lang="zh",
                extra_note=("这是预览，只写这 " + str(len(chunk)) + " 页；不要扩展到其他页。"
                            + (("\n用户补充：" + custom_prompt) if (custom_prompt or "").strip() else "")),
                clamp_pages=True,
            )
        client = DeepSeekClient(model="deepseek-flash")
        try:
            sec = _author(client)
        except Exception:
            _progress(12 + int(40 * (ci - 1) / max(1, len(chunks))), f"第 {ci}/{len(chunks)} 单元：Qwen 重试")
            from tfv2.llm.qwen_text import QwenTextClient
            sec = _author(QwenTextClient(model=os.getenv("TERMFINALE_QWEN_TEXT_MODEL", "qwen-max")))
        mapped = map_facts(local_facts, [sec])
        covered = {x.get("fact_id") or x.get("id") for x in mapped["facts"] if x.get("status") == "covered"}
        for f in local_facts:
            fid = f.get("fact_id") or f["id"]
            if fid not in covered:
                sec.blocks.append(LectureBlock(
                    id=f"fallback-{ci}-{fid}", kind=BlockKind.PARAGRAPH, text=f["text"],
                    source_refs=[SourceRef(material=artifact_id, page_start=f["page"], page_end=f["page"])]))
        sec.source_refs = [SourceRef(material=artifact_id, page_start=1, page_end=len(chunk))]
        sec = normalize_section(sec, list(range(1, len(chunk) + 1)))
        for block in sec.blocks:
            for ref in block.source_refs:
                ref.page_start = min(len(rows), ref.page_start + offset)
                ref.page_end = min(len(rows), ref.page_end + offset)
        for ref in sec.source_refs:
            ref.page_start = min(len(rows), ref.page_start + offset)
            ref.page_end = min(len(rows), ref.page_end + offset)
        for j, row in enumerate(chunk, 1):
            source_text = row.get("text") or ""
            if "[表格]" in source_text or "\n|" in source_text:
                table_text = source_text[source_text.index("[表格]"):] if "[表格]" in source_text else source_text
                sec.blocks.append(LectureBlock(
                    id=f"table-{ci}-{j}", kind=BlockKind.TABLE, text=table_text.strip()[:8000],
                    source_refs=[SourceRef(material=artifact_id, page_start=offset + j, page_end=offset + j)]))
        return sec

    results: dict[int, object] = {}
    workers = min(4, max(1, len(chunks)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_build, ci, chunk, (ci - 1) * chunk_size): ci
                for ci, chunk in enumerate(chunks, 1)}
        done = 0
        for fut in as_completed(futs):
            ci = futs[fut]
            results[ci] = fut.result()
            done += 1
            _progress(12 + int(40 * done / max(1, len(chunks))), f"已完成 {done}/{len(chunks)} 单元")
    sections = [results[i] for i in sorted(results)]
    from tfv2.quality.text_clean import clean_sections, is_generic
    kept = clean_sections(sections)
    if kept == 0:
        raise ValueError("资料文字不足或模型只输出了模板内容，无法生成可靠讲义；请换文字版资料或重新生成")
    for sec in sections:
        sanitize_math(sec)
    if progress:
        progress(58, "正文生成 / 结构整理")

    dst = service.artifact_path(job_id)
    if dst is None:
        dst = paths.data_dir() / "previews" / job_id
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    (dst / "source").mkdir()
    (dst / "source_assets").mkdir()
    candidates = list((src / "source").glob("*.pdf")) + list((src / "source_pdf").glob("*.pdf"))
    if not candidates:
        raise FileNotFoundError("找不到资料 PDF（source/source_pdf）")
    sp = candidates[0]
    d = pymupdf.open(str(sp)); n = pymupdf.open()
    for idx in indices:
        n.insert_pdf(d, from_page=idx, to_page=idx)
    n.save(str(dst / "source" / "scoped.pdf"))
    n.close(); d.close()
    (dst / "source_pages.json").write_text(json.dumps(
        {"version": 1, "material": artifact_id, "page_count": len(rows), "pages": rows},
        ensure_ascii=False, indent=2), encoding="utf-8")
    proj_path = src / "project.json"
    if proj_path.is_file():
        pr = json.loads(proj_path.read_text(encoding="utf-8"))
    else:
        # 只保存了资料、还没生成过讲义时没有 project.json；
        # 预览要能从资料直接出一份可读稿，这里补一个最小合法工程。
        manifest_path = src / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
        title = str(manifest.get("chapter") or manifest.get("artifact") or "资料预览")
        course = str(manifest.get("course") or title)
        first_text = str((rows[0].get("text") or "") if rows else "").strip()
        pr = {
            "id": job_id,
            "chapter_title": title,
            "header": {"title": title, "course": course, "materials": [], "persona": "老师",
                       "coverage_scope": f"{len(all_rows)} 页", "generated_at": ""},
            "summary": {"overview": (first_text[:160] or "这份资料按页整理为可读稿，逐页标注出处。"),
                        "knowledge_map": [], "exam_focus": [], "how_to_use": ""},
            "closing": {"persona": "老师", "text": "先按页读一遍，再回到课程里做练习。"},
            "footer": {"coverage_percent": 100.0, "material_label": title},
            "sections_files": ["sections.json"],
            "page_count": len(all_rows),
            "coverage_percent": 100.0,
            "scope_pages": list(range(1, len(all_rows) + 1)),
            "out_dir": ".",
            "source_file": "source/scoped.pdf",
        }
    pr.update({"id": job_id, "page_count": len(rows), "scope_pages": list(range(1, len(rows) + 1)),
               "source_file": "source/scoped.pdf", "sections_files": ["sections.json"]})
    (dst / "project.json").write_text(json.dumps(pr, ensure_ascii=False, indent=2), encoding="utf-8")
    (dst / "sections.json").write_text(json.dumps([x.model_dump(mode="json") for x in sections], ensure_ascii=False, indent=2), encoding="utf-8")
    if progress:
        progress(82, "排版 / 生成 PDF")
    fallback_pages = sorted(chosen) if page_numbers else list(range(1, len(rows) + 1))
    try:
        build_project(dst / "project.json", pdf=True)
    except ValueError as exc:
        # 公式/矩阵密集的真实教材页会让“成文”类内容体检不通过；
        # 这时不假装成文，改用原页影像 + 页码出处，保证预览可读、可追溯。
        if "内容体检未通过" not in str(exc) and "Gate 未通过" not in str(exc):
            raise
        from tfv2.product.source_digest import build_source_digest
        shutil.rmtree(dst, ignore_errors=True)
        if progress:
            progress(88, "公式页改排原页影像")
        out_dir = build_source_digest(artifact_id, fallback_pages, job_id, scan_mode=True)
        _mark_preview(out_dir if out_dir.is_dir() else out_dir.parent)
        return out_dir / "lecture.pdf" if out_dir.is_dir() else out_dir
    _mark_preview(dst)
    if progress:
        progress(100, "预览完成")
    return dst / "lecture.pdf"
