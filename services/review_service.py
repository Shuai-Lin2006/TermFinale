"""复习模式服务：逻辑分析 / 资料提取 / 训练试卷。

v2 变化：
- 逻辑分析合并为一次生成（图谱 + 因果链 + 对照表），不再二选一；
- 提取改为**按页打包**，并做去重与覆盖统计（能说清"这次处理了多少页、多少块有产出"）。
"""
from __future__ import annotations

import re
import threading
import time

from loguru import logger

from core.database import GeneratedFile as DBGeneratedFile, get_db_session
from core.exam_engine import (
    generate_exam_paper,
    generate_extraction,
    generate_logic_analysis,
    generate_logic_bundle,
)
from core.exporter import export_to_html
from core.lang_convert import to_hant
from core.generate.exam_builder import blueprint_from_sections, build_blueprint
from core.quality.constraints import (
    TaskConstraints,
    default_constraints,
    render_prompt,
    scope_pages,
    source_pages,
    validate_output,
)
from core.quality.gate import ConstraintViolation, aggregate_reports, generate_until_valid
from services.guide_service import build_course_info
from services.task import (
    ProgressCb,
    ProgressEvent,
    RunResult,
    default_output_dir,
    dump_debug,
    noop_progress,
)

EXTRACT_CHUNK = 2000
PAGE_SPLIT = re.compile(r"(?=【《[^》]+》第\s*\d+\s*页】)")


# --------------------------------------------------------------------------- #
# 切块与去重（纯函数，可单测）
# --------------------------------------------------------------------------- #
def split_pages(text: str) -> list[str]:
    """按解析器写入的页头切页；没有页头时整段当一页。"""
    parts = [p for p in PAGE_SPLIT.split(text or "") if p.strip()]
    return parts or ([text] if text and text.strip() else [])


def pack_pages(pages: list[str], limit: int = EXTRACT_CHUNK, overlap: int = 300) -> list[str]:
    """把页装进不超过 limit 的块；块之间带上一页尾部重叠，避免跨页题被切断。"""
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for page in pages:
        if buf and size + len(page) > limit:
            chunks.append("\n\n".join(buf))
            tail = buf[-1][-overlap:] if len(buf[-1]) > overlap else buf[-1]
            buf = [f"【接上页，若与本题相关请合并成完整一题】\n{tail}"]
            size = len(buf[0])
        buf.append(page)
        size += len(page)
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def split_text_safely(text: str, size: int = EXTRACT_CHUNK) -> list[str]:
    """兼容旧接口：无页头时的安全切块（不切断 [[[IMAGE:]]]）。"""
    chunks: list[str] = []
    start, n = 0, len(text)
    while start < n:
        end = min(n, start + size)
        if end < n:
            tag_start = text.rfind("[[[IMAGE:", start, end)
            if tag_start != -1 and text.find("]]]", tag_start, end) == -1:
                end = tag_start
            if end - start > size // 2:
                para = text.rfind("\n\n", start + size // 2, end)
                if para != -1:
                    end = para
        if end <= start:
            end = min(n, start + size)
        chunks.append(text[start:end])
        start = end
    return [c for c in chunks if c.strip()]


def _fingerprint(text: str) -> str:
    cleaned = re.sub(r"[\s*#\-—:：，,。.、()（）\[\]【】<>《》\"']", "", text)
    return cleaned[:48]


def dedupe_markdown(markdown: str) -> tuple[str, int]:
    """按块指纹去重，保留首次出现顺序。返回 (结果, 删掉的块数)。"""
    blocks = re.split(r"\n\s*\n", markdown or "")
    if len(blocks) <= 1:
        blocks = [line for line in (markdown or "").splitlines() if line.strip()]

    seen: set[str] = set()
    kept: list[str] = []
    removed = 0
    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue
        if len(stripped) >= 20:
            fp = _fingerprint(stripped)
            if fp and fp in seen:
                removed += 1
                continue
            seen.add(fp)
        kept.append(stripped)
    return "\n\n".join(kept), removed


# --------------------------------------------------------------------------- #
# 提取
# --------------------------------------------------------------------------- #
def _run_extract(text: str, extract_type: str | None, with_answer: bool,
                 on_progress: ProgressCb, stop_event: threading.Event,
                 started: float, user_note: str = "",
                 constraints: TaskConstraints | None = None) -> tuple[str, dict, object]:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    constraints = constraints or default_constraints(
        "extract", extract_type=extract_type, with_answer=with_answer)
    constraint_block = render_prompt(constraints)

    pages = split_pages(text)  # 全书分块，不再截断前 20 页
    if constraints.has_scope:
        before = len(pages)
        pages = scope_pages(pages, constraints)
        logger.info("提取范围 {}：{} 页 → {} 页", constraints.scope_label(), before, len(pages))
        if not pages:
            raise RuntimeError(f"所选页码范围（{constraints.scope_label()}）内没有解析到任何内容")
    chunks = (pages if len(pages) <= 150 else pack_pages(pages)) if pages else []
    if not chunks:
        return "", {"coverage": 0}, None
    results: list[str] = [""] * len(chunks)
    reports: dict[int, object] = {}
    done = 0

    def work(i: int, chunk: str) -> tuple[int, str, object]:
        import time as _t
        _t0 = _t.time()
        if stop_event.is_set():
            return i, "", None
        allowed = source_pages(chunk)
        if allowed and min(allowed) > 1:
            allowed.add(min(allowed) - 1)  # 跨页合并的题可能引用上一页

        def _gen(feedback: str) -> str:
            note = (user_note or "") + "\n本块必须逐页输出：每页至少一条要点，并在每条开头保留页码（第X页），不得跳过任何页。"
            if feedback:
                note += "\n\n" + feedback
            md = generate_extraction(chunk, extract_type, with_answer, user_note=note,
                                     constraint_block=constraint_block)
            if not md.strip():
                try:
                    from core.exam_engine import _qwen_fallback
                    md = _qwen_fallback(
                        "你是大学期末复习资料提取助手。只输出结构化考点，中文，不要解释过程。",
                        chunk[:4000], max_tokens=2500)
                except Exception:
                    pass
            return md

        md, report = generate_until_valid(
            _gen, constraints, source_text=chunk,
            allowed_pages=allowed or None, stage="chunk", raise_on_fail=False)
        if not md.strip():
            # 空块是覆盖率问题（图片页/无考点页），交给最终覆盖率报出来，
            # 不按硬违规整篇判失败；重试已在本函数内完成。
            report.issues.clear()
            report.warn("区块无产出（已重试）")
        logger.info("extract chunk {} type={} sec={:.1f} chars={} attempts={}",
                    i, extract_type, _t.time() - _t0, len(md or ""),
                    report.metrics.get("attempts"))
        return i, md, report

    with ThreadPoolExecutor(max_workers=min(2, len(chunks))) as pool:
        futures = [pool.submit(work, i, c) for i, c in enumerate(chunks)]
        for fut in as_completed(futures):
            try:
                i, md, report = fut.result()
            except Exception as exc:  # noqa: BLE001
                logger.warning("提取区块失败: {}", exc)
                continue
            if report is not None:
                reports[i] = report
            if md:
                md = re.sub(r"以下是.*?考题。", "", md)
                md = re.sub(r"以下是.*?提取.*?：", "", md)
                results[i] = md
            done += 1
            on_progress(ProgressEvent(
                f"🔍 已提取 {done}/{len(chunks)} 个区块（并发 2）...",
                done / len(chunks)))

    # 空块再补一次（重试已经跑过，这里只兜底极少数瞬时失败）
    _missing = [i for i, r in enumerate(results) if not (r or "").strip()]
    for _i in _missing[:5]:
        try:
            _md = generate_extraction(chunks[_i], extract_type, with_answer,
                                      constraint_block=constraint_block,
                                      user_note=user_note)
            if _md and _md.strip():
                results[_i] = _md
                logger.info("空块补跑成功 chunk={}", _i)
        except Exception as _e:
            logger.warning("空块补跑失败 chunk={} err={}", _i, str(_e)[:80])

    # 按页覆盖补跑：块里有的页完全没被引用时补跑该块（最多 8 块，控制成本）
    def _pages(t):
        return set(re.findall(r"第\s*(\d+)\s*页", t or ""))
    _cited_now = set()
    for _r in results:
        _cited_now |= _pages(_r)
    _need = [i for i, _chunk in enumerate(chunks) if (_pages(_chunk) - _cited_now)]
    for _i in _need[:8]:
        _want = _pages(chunks[_i])
        try:
            _md = generate_extraction(
                chunks[_i], extract_type, with_answer, constraint_block=constraint_block,
                user_note=(user_note or "") + "\n请逐页输出，保留页码，不得跳过任何页。")
            if _md and _md.strip():
                results[_i] = _md
                _cited_now |= _pages(_md)
                logger.info("缺页块补跑 chunk={} 补页={}", _i, sorted(_want - _pages(_md))[:8])
        except Exception as _e:
            logger.warning("缺页块补跑失败 chunk={} err={}", _i, str(_e)[:80])
    ok_chunks = sum(1 for r in results if r and r.strip())
    merged, removed = dedupe_markdown("\n\n".join(results))
    _cited = set(re.findall(r"第\s*(\d+)\s*页", merged))
    coverage = {
        "pages": len(pages),
        "pages_cited": len(_cited),
        "chunks": len(chunks),
        "chunks_ok": ok_chunks,
        "attempts": sum(int(getattr(r, "metrics", {}).get("attempts", 1)) for r in reports.values()),
        "duplicates_removed": removed,
        "coverage": round(ok_chunks / len(chunks), 3) if chunks else 0.0,
    }
    report = aggregate_reports("extract", reports)
    logger.info("提取完成：{} 页 / {} 块 / 去重 {} 块", len(pages), len(chunks), removed)
    return merged, coverage, report


Q_START = re.compile(r"^\s*(?:\*\*)?(?:\d{1,2}\s*[.、．)）]|【例)", re.MULTILINE)


def escape_question_numbers(markdown: str) -> str:
    """保留资料原始题号，只把行首 "1." 变成 "**1.**"，避免被 Markdown 当成有序列表重排。"""
    return re.sub(r"(?m)^(\s*)(\d{1,2})([.、．])\s*", r"\1**\2\3** ", markdown or "")


def insert_answer_blanks(markdown: str, height: int = 150) -> str:
    """练习题：每道题结束后插入答题留白（题号保持原样）。"""
    parts = re.split(r"(?m)(?=^\s*(?:\*\*)?(?:\d{1,2}\s*[.、．)）]|【例))", markdown or "")
    out = []
    for part in parts:
        if not part.strip():
            continue
        if Q_START.match(part):
            part = part.rstrip() + f"\n\n[[BLANK:{height}]]"
        out.append(part.rstrip())
    return "\n\n".join(out)


def add_answer_space(markdown: str, height: int = 150) -> str:
    return insert_answer_blanks(escape_question_numbers(markdown), height)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def run_review(
    course: dict,
    task_type: str,
    text: str,
    *,
    extract_type: str | None = None,
    with_answer: bool = True,
    mode: str = "bundle",
    train_type: str | None = None,
    num_sets: int = 1,
    difficulty: int = 3,
    diy_config: str = "",
    user_context: dict | None = None,
    sections: list | None = None,
    reference_exam: bool = False,
    material_mode: str = "exam",
    lang: str = "中文",
    user_note: str = "",
    on_progress: ProgressCb = noop_progress,
    stop_event: threading.Event | None = None,
    constraints: TaskConstraints | None = None,
) -> RunResult | None:
    """task_type: analysis / extract / exam。被中断时返回 None。"""
    stop_event = stop_event or threading.Event()
    started = time.time()
    on_progress(ProgressEvent("📚 正在整理资料并分块…", 0.04))
    info = build_course_info(course)
    extra_metrics: dict = {}
    warnings: list[str] = []
    constraints = constraints or default_constraints(
        task_type, extract_type=extract_type, with_answer=with_answer,
        material_kind=material_mode, sections=sections)
    if task_type == "extract":
        constraints.extract_type = extract_type or constraints.extract_type or "points"
    constraint_block = render_prompt(constraints)
    validation = None

    if task_type == "extract":
        markdown, coverage, extract_report = _run_extract(
            text, extract_type, with_answer, on_progress, stop_event, started, user_note,
            constraints=constraints)
        if stop_event.is_set():
            return None
        doc_name = "练习卷" if (extract_type == "questions" and not with_answer) else "资料提取"
        if extract_type == "questions":
            markdown = escape_question_numbers(markdown)
            if not with_answer:
                markdown = insert_answer_blanks(markdown)
        extra_metrics["coverage"] = coverage
        if coverage["coverage"] < 1.0:
            warnings.append(
                f"有 {coverage['chunks'] - coverage['chunks_ok']} 个区块没有产出，可能漏内容")
        if extract_report is not None:
            warnings.extend(extract_report.warnings)
            extra_metrics["block_attempts"] = int(extract_report.metrics.get("attempts", 1))

    elif task_type == "analysis":
        on_progress(ProgressEvent("🧠 AI 正在构建知识地图与因果链...", 0.4))

        def _gen_analysis(feedback: str) -> str:
            if mode == "bundle":
                return generate_logic_bundle(text, lang, user_note=user_note,
                                             constraint_block=constraint_block,
                                             retry_note=feedback)
            return generate_logic_analysis(text, mode, user_note=user_note,
                                           constraint_block=constraint_block,
                                           retry_note=feedback)

        markdown, report = generate_until_valid(
            _gen_analysis, constraints, source_text=text, stage="final")
        doc_name = "逻辑分析" if mode in ("bundle", "text_logic") else "思维导图"
        warnings.extend(report.warnings)
        validation = report
        if stop_event.is_set():
            return None

    elif task_type == "exam":
        on_progress(ProgressEvent("📝 命题组长正在疯狂敲键盘，为你量身定制期末试卷...", 0.4))
        blueprint = None
        if sections:
            blueprint = blueprint_from_sections(sections, lang)
        elif not diy_config:
            blueprint = build_blueprint(difficulty, (user_context or {}).get("target_score", 80), lang)
        if blueprint is not None:
            # 生成与校验共用同一份结构
            constraints.sections = [{"name": s.name, "count": s.count, "points": s.each}
                                    for s in blueprint.sections]
            constraint_block = render_prompt(constraints)
        exam_note = user_note + ("\n注意：资料更像课堂讲义，题型与考点为推测。"
                                 if material_mode == "lecture" else "")

        def _gen_exam(feedback: str) -> str:
            return generate_exam_paper(
                text, train_type, num_sets, difficulty,
                diy_config=diy_config,
                user_context=user_context, lang=lang, blueprint=blueprint,
                sections=sections, reference_exam=reference_exam,
                user_note=exam_note, constraint_block=constraint_block,
                retry_note=feedback,
                with_answers=(constraints.answer_mode == "required"),
                course_name=course.get("name", ""))

        markdown, report = generate_until_valid(
            _gen_exam, constraints, source_text=text, stage="final")
        extra_metrics["paper"] = report.metrics
        warnings.extend(report.warnings)
        validation = report
        doc_name = "训练试卷"
        if stop_event.is_set():
            return None

    else:
        raise ValueError(f"未知的任务类型: {task_type}")

    if task_type == "extract":
        # 合并后的最终校验：排除项、页码范围、考点出处、答案要求
        final_report = validate_output(markdown, constraints, source_text=text, stage="final")
        warnings.extend(final_report.warnings)
        validation = final_report
        if not final_report.ok:
            logger.warning("提取最终校验未通过: {}", final_report.issues[:5])
            if constraints.strict:
                dump_debug("extract_rejected", markdown,
                           {"constraints": constraints.to_dict(),
                            "validation": final_report.to_dict()})
                raise ConstraintViolation(final_report)
            warnings.extend(final_report.issues)

    if not markdown:
        raise RuntimeError("生成结果为空")

    on_progress(ProgressEvent("🎨 正在渲染排版，并为你检查公式与换行...", 0.8))

    time_str = time.strftime("%m%d_%H%M", time.localtime())
    output_path = str(default_output_dir() / f"{course['name']}_{doc_name}_{time_str}.html")

    if lang in ("繁體中文", "繁体中文", "zh-Hant"):
        markdown = to_hant(markdown)
    elif lang == "English":
        from core.lang_convert import to_english
        markdown = to_english(markdown)
    export_to_html(markdown, output_file=output_path, course=info, persona="AI",
                   doc_type=doc_name, lang=lang)

    db = get_db_session()
    try:
        import json as _json
        from pathlib import Path as _Path
        _meta = {"lang": lang, "extract_type": extract_type, "with_answer": with_answer,
                 "train_type": train_type, "num_sets": num_sets, "difficulty": difficulty,
                 "materials_used": len(course.get("materials") or [])}
        _Path(output_path).with_suffix(".json").write_text(_json.dumps(_meta, ensure_ascii=False), encoding="utf-8")
        db.add(DBGeneratedFile(course_id=course["id"], file_path=output_path,
                               created_at=time_str, file_type=task_type))
        db.commit()
    finally:
        db.close()

    metrics = {
        "kind": task_type,
        "doc_type": doc_name,
        "chars": len(markdown),
        "elapsed_s": round(time.time() - started, 1),
        "lang": lang,
        "constraints": constraints.to_dict(),
        "validation": validation.to_dict() if validation is not None else None,
        **extra_metrics,
    }
    dump_debug(task_type, markdown, metrics)

    on_progress(ProgressEvent("✅ 渲染成功，准备展示！", 1.0))
    time.sleep(0.5)

    warnings = list(dict.fromkeys(warnings))[:20]
    return RunResult(output_path=output_path, doc_type=doc_name, markdown=markdown,
                     metrics=metrics, warnings=warnings)
