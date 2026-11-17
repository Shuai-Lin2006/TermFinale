"""多资料合并生成：多份资料按权重合并成一份讲义。

先把每份资料转成 PDF，再按输入顺序拼成一个 PDF；每一页记录属于哪份资料。
高权重资料切得更细（每段页数更少），从而获得更多小节/篇幅；这不是只写进 prompt。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from core.platform_utils import find_soffice
from tfv2.authoring.lecture import AuthoringError, author_section, author_wrapup, fallback_wrapup, normalize_lecture_sections
from tfv2.build import build_project
from tfv2.domain.lecture import (
    BlockKind,
    LanguagePolicy,
    LectureBlock,
    LectureClosing,
    LectureFooter,
    LectureHeader,
    LectureSummary,
    SourceRef,
)
from tfv2.domain.page import PageQuality
from tfv2.llm.client import DeepSeekClient, LLMError
from tfv2.product import generate, service
from tfv2.product.requirements import interpret_requirements, requirement_prompt


class MultiError(RuntimeError):
    pass


def _to_pdf(source: Path, out_dir: Path) -> Path:
    suffix = source.suffix.lower()
    if suffix == ".pdf":
        target = out_dir / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        return target
    if suffix in (".png", ".jpg", ".jpeg", ".webp"):
        return generate._image_to_pdf(source, out_dir)
    if suffix in (".pptx", ".docx", ".ppt", ".doc"):
        exe = find_soffice()
        if not exe:
            raise MultiError("PPT/PPTX/DOCX 需要本机安装 LibreOffice（soffice）")
        out_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [exe, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(source)],
            check=False, capture_output=True, text=True, timeout=240,
        )
        pdf = out_dir / f"{source.stem}.pdf"
        if not pdf.is_file():
            raise MultiError(f"{source.name} 转 PDF 失败")
        return pdf
    raise MultiError(f"多资料合并暂不支持 {suffix}；请用 PDF/PPT/PPTX/DOCX")


def _chapter_rank(name: str) -> int:
    m = re.search(r"(?:第\s*([0-9一二三四五六七八九十百]+)\s*[章节]|chapter\s*([0-9]+))", name or "", re.I)
    if not m:
        return 9999
    raw = m.group(1) or m.group(2) or ""
    if raw.isdigit():
        return int(raw)
    digits = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if raw == "十":
        return 10
    m2 = re.fullmatch(r"([一二三四五六七八九]?)十([一二三四五六七八九]?)", raw)
    if m2:
        return (digits.get(m2.group(1), 1)) * 10 + digits.get(m2.group(2), 0)
    return digits.get(raw, 9999)


def _sort_sources(sources: list[tuple[Path, float]]) -> list[tuple[Path, float]]:
    ranked = [(i, _chapter_rank(p.name), p, w) for i, (p, w) in enumerate(sources)]
    if not any(r < 9999 for _, r, _, _ in ranked):
        return sources
    return [(p, w) for _, _, p, w in sorted(ranked, key=lambda x: (x[1], x[0]))]


TIER_FACTOR = {"985": 1.08, "211": 1.06, "一本": 1.03, "二本": 1.0, "专科高职": 0.94}


def _cn_size(weight: float, school_level: str = "") -> int:
    # 层级只做很小幅度的难度权重修正，避免极端差异。
    factor = TIER_FACTOR.get((school_level or "").strip(), 1.0)
    effective = max(1.0, min(5.0, float(weight) * factor))
    return max(6, min(10, int(round(10 - 0.8 * effective))))


def _plan(ranges: list[dict], school_level: str = "") -> list[tuple[str, list[int], str, float]]:
    plan: list[tuple[str, list[int], str, float]] = []
    for item in ranges:
        pages = list(range(item["start"], item["end"] + 1))
        size = _cn_size(float(item["weight"]), school_level)
        for i in range(0, len(pages), size):
            group = pages[i:i + size]
            local_start = group[0] - item["start"] + 1
            local_end = group[-1] - item["start"] + 1
            plan.append((f"{item['name']}（权重 {item['weight']:g}）· 资料第 {local_start}–{local_end} 页 / 合订本第 {group[0]}–{group[-1]} 页",
                         group, item["name"], float(item["weight"])))
    return plan


def generate_multi(
    sources: list[tuple[Path, float]],
    *,
    title: str,
    course: str = "",
    target_score: int | None = 80,
    days_left: int | None = 7,
    foundation: str = "基础较弱",
    persona: str = "老师",
    key_points: str = "",
    excluded: str = "",
    custom_prompt: str = "",
    gen_lang: str = "zh",
    school_level: str = "",
    progress: generate._PROGRESS | None = None,
) -> dict:
    if not sources:
        raise MultiError("没有上传资料")
    # 文件顺序由用户在“新建讲义”里明确调整；这里不再用文件名覆盖用户选择。
    title = (title or "").strip() or "多资料合并讲义"
    course = (course or "").strip() or title
    target_score = max(60, min(100, int(target_score or 80)))
    days_left = max(1, min(30, int(days_left or 7)))
    aid = generate._new_id()
    out = generate.ARTIFACT_ROOT / aid
    out.mkdir(parents=True, exist_ok=False)
    (out / "source").mkdir()
    image_dir = out / "source_assets"
    image_dir.mkdir()

    # 1) 转 PDF + 拼合
    try:
        import pymupdf
        combined = pymupdf.open()
        ranges: list[dict] = []
        cursor = 0
        for idx, (source, weight) in enumerate(sources, start=1):
            if not source.is_file():
                raise MultiError(f"资料不存在：{source}")
            pdf = _to_pdf(source, out / "source")
            doc = pymupdf.open(str(pdf))
            n = len(doc)
            combined.insert_pdf(doc)
            ranges.append({"name": source.name, "weight": float(weight),
                           "start": cursor + 1, "end": cursor + n})
            cursor += n
            doc.close()
            if progress:
                progress(4 + idx, f"合并 {idx}/{len(sources)}：{source.name}（{n} 页）")
        combined_pdf = out / "source" / "combined.pdf"
        combined.save(str(combined_pdf))
        combined.close()
    except MultiError:
        shutil.rmtree(out, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(out, ignore_errors=True)
        raise MultiError(f"资料合并失败：{exc}") from exc

    page_count = cursor
    if page_count < 1:
        shutil.rmtree(out, ignore_errors=True)
        raise MultiError("合并后没有页面")
    try:
        ledger = generate._ledger(combined_pdf, image_dir)
        generate._add_page_scans(ledger, combined_pdf, image_dir)
        generate._preclassify_slide_figures(ledger)
    except Exception as exc:
        shutil.rmtree(out, ignore_errors=True)
        raise MultiError(f"资料解析失败：{exc}") from exc

    plan = _plan(ranges, school_level)
    if len(plan) > 30:
        # 权重切得太碎：退化为 10 页/段，保证能生成
        plan = []
        for item in ranges:
            pages = list(range(item["start"], item["end"] + 1))
            for i in range(0, len(pages), 10):
                group = pages[i:i + 10]
                local_start = group[0] - item["start"] + 1
                local_end = group[-1] - item["start"] + 1
                plan.append((f"{item['name']}（权重 {item['weight']:g}）· 资料第 {local_start}–{local_end} 页 / 合订本第 {group[0]}–{group[-1]} 页",
                             group, item["name"], float(item["weight"])))
    if len(plan) > 30:
        shutil.rmtree(out, ignore_errors=True)
        raise MultiError(f"合并后 {page_count} 页切成 {len(plan)} 段，超过 30 段；请减少资料或拆分")

    try:
        client = DeepSeekClient()
    except Exception as exc:
        shutil.rmtree(out, ignore_errors=True)
        raise MultiError(f"模型客户端不可用：{exc}") from exc

    requirements = interpret_requirements(
        client, key_points=key_points, excluded=excluded, custom_prompt=custom_prompt,
        title=title, course=course, target_score=target_score, days_left=days_left,
        foundation=foundation, persona=persona, gen_lang=gen_lang,
    )
    req_prompt = requirement_prompt(requirements)
    chapter_title = title.strip() or "多资料合并讲义"
    page_text_by_no = {p.page_no: (p.text or "") for p in ledger.pages}
    page_by_no = {p.page_no: p for p in ledger.pages}
    weighted = [(x["label"], x["weight"]) for x in requirements.get("must_cover", [])]
    sections = []
    previous = ""
    for i, (label, pages, material, weight) in enumerate(plan, start=1):
        display_label = generate._section_label(label, i)
        if progress:
            progress(10 + int(70 * (i - 1) / len(plan)), f"生成第 {i}/{len(plan)} 段：{display_label}")
        section = None
        last = ""
        for attempt in range(2):
            note = (
                f"本段来自《{material}》，资料权重 {weight:g}/5，资料页："
                + "、".join(map(str, pages)) + "。"
                "每个 block 的 source_pages 必须从这些页码取，且每页至少出现一次；"
                "权重越高，正文越要展开、越要给出可跟做的例题/易错；不能只列结论。"
                "资料没有例题不要硬编；公式用 $...$。"
                + (f" 学校层级：{school_level}；按这个层级的常见要求调整推导详略，但不要夸大难度。" if school_level else "")
            )
            if req_prompt:
                note += "\n用户需求（已由需求理解 Agent 结构化，必须按语义执行）：\n" + req_prompt
            if weight >= 4:
                note += " 这是高权重资料：至少两个自然段加一个例题/易错，不能压缩成摘要。"
            rel = [(t, w) for t, w in weighted if t in display_label or t in " ".join(page_text_by_no.get(p, "") for p in pages)]
            if rel:
                note += " 用户重点权重：" + "、".join(f"{t}={w}" for t, w in rel) + "。"
            if previous:
                note += f" 上一节是《{previous[:260]}》。本节开头要自然承接上一节，避免重复，也不要跳回更早资料；保持从第一章第一节向后的顺序。"
            try:
                section = author_section(
                    client, ledger, chapter_title=chapter_title, section_title=display_label,
                    pages=pages, target_score=target_score, days_left=days_left,
                    foundation=foundation, persona=persona, extra_note=note, gen_lang=gen_lang,
                )
            except (AuthoringError, LLMError) as exc:
                last = str(exc)
                section = None
                continue
            candidate = generate._attach_figures(section.model_copy(deep=True), ledger, pages)
            # 空白页/纯图片页不可能被模型写成正文；保留来源页并显式标注，
            # 不能因为模型无法引用而把整份多资料讲义丢掉。
            for pno in sorted(set(pages) - generate._cited_pages(candidate)):
                page = page_by_no.get(pno)
                if page is None or (page.text or "").strip() or page.quality == PageQuality.TEXT:
                    continue
                candidate.blocks.append(LectureBlock(
                    id=f"blank-{i}-{pno}", kind=BlockKind.PARAGRAPH,
                    text="本页为空白页或图片页，原资料没有可提取的正文内容。",
                    source_refs=[SourceRef(material=material, page_start=pno, page_end=pno)],
                ))
            missing = sorted(set(pages) - generate._cited_pages(candidate))
            if missing and attempt == 1:
                # 模型两次仍未引用这些页：保住用户资料，不让整份失败。
                for pno in missing:
                    page = page_by_no.get(pno)
                    raw = (page.text or "").strip() if page is not None else ""
                    if not raw:
                        continue
                    candidate.blocks.append(LectureBlock(
                        id=f"source-fallback-{i}-{pno}", kind=BlockKind.PARAGRAPH,
                        text=f"资料补充（第 {pno} 页）：{raw[:1800]}",
                        source_refs=[SourceRef(material=material, page_start=pno, page_end=pno)],
                    ))
                missing = sorted(set(pages) - generate._cited_pages(candidate))
            if not missing:
                section = candidate
                break
            last = "页面没有被任何 block 引用：" + "、".join(map(str, missing))
            if last:
                note += " 上次缺少页码：" + "、".join(map(str, missing)) + "；这次必须写到正文。"
            section = None
        if section is None:
            shutil.rmtree(out, ignore_errors=True)
            raise MultiError(f"{display_label} 生成失败：{last}")
        if any(x in section.title for x in (".pdf", "资料第", "合订本", "权重", "正文")):
            base = re.sub(r"\.(pdf|pptx|docx)$", "", material, flags=re.I)
            base = re.sub(r"\s*\(\d+\)$", "", base).strip()
            src_range = next((r for r in ranges if r.get("name") == material), None)
            offset = int(src_range.get("start", 1)) - 1 if src_range else 0
            local_start = min(pages) - offset
            local_end = max(pages) - offset
            span = str(local_start) if local_start == local_end else f"{local_start}–{local_end}"
            short = generate._fallback_title(section, i).strip("… ")
            short = re.sub(r"^(小结|本节小结|小结一下|本节要点)[：:]\s*", "", short).strip()
            short = re.sub(r"^(从|围绕|本讲义|这一节)[^，。；]*[，。；]", "", short).strip()
            if len(short) > 22:
                short = short[:22] + "…"
            section.title = f"{base} / {short}" if base and short else (f"{base} / 第 {span} 页" if base else short)
        sections.append(section)
        previous = section.title
        if section.summary:
            previous += "。小结：" + section.summary[:220]
    if gen_lang == "hant":
        generate._hant_sections(sections)
    generate._dedupe_titles(sections)

    # 用户需求已由需求理解 Agent 结构化进入 prompt；不做字面关键词硬校验。 from exc

    (out / "sections.json").write_text(
        json.dumps([s.model_dump(mode="json") for s in sections], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    normalize_lecture_sections(sections, gen_lang)
    kmap = generate._make_knowledge_map(title, sections, out, gen_lang)
    if kmap and sections:
        try:
            from tfv2.domain.lecture import FigureRef
            cap = "章知识地图（系统根据本讲义目录生成，非资料原图）" if gen_lang != "en" else "Chapter knowledge map (generated from this outline; not a source figure)"
            sections[0].blocks.insert(0, LectureBlock(
                id=f"generated-map-{aid}", kind=BlockKind.FIGURE, text="", source_refs=[],
                figure=FigureRef(
                    image_id=f"generated-map-{aid}", caption=cap,
                    source=SourceRef(material="多资料合集", page_start=1, page_end=1),
                    after_block_id=f"generated-map-{aid}", asset_path="assets/generated_knowledge_map.png",
                    origin="schematic",
                    source_note="由讲义目录自动绘制的章节结构图；用于导航，不冒充资料原图。",
                ),
            ))
        except Exception:
            pass
    materials_text = "；".join(
        f"{r['name']}（权重 {r['weight']:g}，第 {r['start']}–{r['end']} 页）" for r in ranges
    )
    header = LectureHeader(
        title=title, course=course, section_label=f"{len(ranges)} 份资料 · {len(sections)} 节 · {page_count} 页",
        materials=[],
        target_score=target_score, days_left=days_left, foundation=foundation, persona=persona,
        coverage_scope=f"{page_count} 页",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    focus = [f"{t}（权重 {w}）" for t, w in weighted]
    summaries = []
    for sec in sections:
        for block in sec.blocks:
            if block.kind.value == "summary" and block.text:
                text = block.text.replace("小结一下：", "").replace("小结：", "").replace("本节小结：", "").strip()
                if text:
                    summaries.append(text)
    wrap = author_wrapup(
        client, title=title, course=course, sections=sections, persona=persona,
        foundation=foundation, target_score=target_score, days_left=days_left, gen_lang=gen_lang,
    )
    fallback = fallback_wrapup(sections, title, persona, gen_lang)
    def _clean_points(items):
        out = []
        for raw in items or []:
            text = str(raw or "").strip().lstrip("-•· ").strip()
            text = text.replace("…", "").replace("...", "").strip(" ，,。；;：:")
            text = re.sub(r"^\d+[.、]\s*", "", text)
            if 3 <= len(text) <= 28 and text not in out:
                out.append(text)
        return out[:8]
    overview = (wrap.overview or fallback.overview).strip()
    points = _clean_points(wrap.knowledge_map) or fallback.knowledge_map
    closing_text = (wrap.closing or fallback.closing).strip()
    if len(closing_text) < 300 or len(re.findall(r"[。.!！?？]", closing_text)) < 5:
        closing_text = fallback.closing
    if gen_lang == "en":
        summary = LectureSummary(
            overview=overview[:1800], knowledge_map=points, exam_focus=focus,
            how_to_use="Read the summary, then each section: intuition → example → practice. Check the source page when a step is unclear.",
        )
        disclaimer = "For study reference only; always check the original material. This material assumes no legal liability."
        material_label = f"Multi-source collection ({len(ranges)} sources)"
    else:
        summary = LectureSummary(
            overview=generate._tr(overview[:2200], gen_lang),
            knowledge_map=[generate._tr(x, gen_lang) for x in points], exam_focus=focus,
            how_to_use=generate._tr("先读每节摘要，再按节跟例题做一遍；遇到单位、基准或边界条件不清时回看该节出处。", gen_lang),
        )
        disclaimer = generate._tr("具体请以实际资料为准，本资料不承担由此产生的法律责任。", gen_lang)
        material_label = generate._tr(f"多资料合集（{len(ranges)} 份）", gen_lang)
    closing = LectureClosing(persona=persona, text=closing_text)
    footer = LectureFooter(
        agent_name="TermFinale", coverage_percent=100, material_label=material_label, disclaimer=disclaimer,
    )
    project = {
        "id": aid, "chapter_title": chapter_title, "header": header.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"), "closing": closing.model_dump(mode="json"),
        "footer": footer.model_dump(mode="json"), "sections_files": ["sections.json"],
        "page_count": page_count, "coverage_percent": 100,
        "scope_pages": list(range(1, page_count + 1)), "overview_pages": [],
        "constraints": {
            "key_points": key_points, "excluded": excluded, "custom_prompt": custom_prompt,
            "requirements": requirements,
            "materials": ranges,
        },
        "source_file": "source/combined.pdf", "assets_dir": "source_assets",
        "out_dir": ".", "language_policy": LanguagePolicy(
            ui_lang="zh", gen_lang=generate.GEN_LANG_LABEL.get(gen_lang, "简体中文"),
            source_lang=None, translation_mode="none",
        ).model_dump(mode="json"),
    }
    (out / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        build_project(out / "project.json", pdf=True)
    except Exception as exc:
        shutil.rmtree(out, ignore_errors=True)
        raise MultiError(f"Gate/PDF 未通过，不能交付：{exc}") from exc
    artifact = service.get_artifact(aid)
    return {"id": aid, "artifact": artifact, "pages": page_count,
            "sections": len(sections), "coverage_percent": 100,
            "materials": ranges, "outline_used": False}
