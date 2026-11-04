"""讲义生成服务：解析资料 → 规划大纲 → 逐章生成 → 校验 → 渲染 HTML。

与 v1 的差别：
1. 不再按「2 页一块」硬切，而是**先出大纲**，再按章节生成；
2. 每章带「必须覆盖 / 前后章 / 篇幅」约束，减少跑题与重复；
3. 每章生成后跑 `qa.check_markdown`，指标写进 debug；
4. 进度通过回调上报；原始 Markdown + 指标落盘。
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import re
import threading
import time

from loguru import logger

from core.ai_engine import generate_super_guide
from core.database import GeneratedFile as DBGeneratedFile, Material as DBMaterial, get_db_session
from core.exam_engine import call_ai_with_retry
from core.exporter import export_to_html
from core.generate import outline_store
from core.generate.outline import Chapter, Outline, generate_outline
from core.parser import extract_text_from_file
from core.personas import OUTROS
from core.quality.qa import check_chapters
from models.user_profile import CourseInfo
from services.task import (
    ProgressCb,
    ProgressEvent,
    RunResult,
    default_output_dir,
    dump_debug,
    noop_progress,
)

MAX_PAGES = 15
PAGES_PER_CALL = 3          # 单次请求最多塞 3 页，避免输入过长导致输出被挤压


def _concurrency() -> int:
    """并发生成度：默认 2，可用 TERMFINALE_CONCURRENCY 调整（1~4）。"""
    try:
        return max(1, min(4, int(os.getenv("TERMFINALE_CONCURRENCY", "2"))))
    except ValueError:
        return 1


# --------------------------------------------------------------------------- #
# 纯函数（可单测）
# --------------------------------------------------------------------------- #
def build_weight_prompt(core_pages: list, ref_pages: list, core_ratio: float) -> str:
    if core_pages and ref_pages:
        if core_ratio > 0.5:
            return (f"本轮生成以【核心重点】为绝对主导（占 {int(core_ratio * 100)}%），"
                    "【参考资料】仅作辅助补充。遇到冲突时，必须无条件以核心重点为准！")
        if core_ratio < 0.5:
            return (f"本轮生成以【参考资料】为主要框架（占 {int((1 - core_ratio) * 100)}%），"
                    "【核心重点】作为点睛之笔。")
        return "本轮生成综合参考【核心重点】与【参考资料】，请提取双方的精华进行融合。"
    if core_pages:
        return "本轮生成纯粹基于【核心重点】，禁止自行发散。"
    if ref_pages:
        return "本轮生成纯粹基于【参考资料】，请仔细梳理全部知识点。"
    return ""


def truncate_pages(core_pages: list, ref_pages: list, core_ratio: float) -> tuple[list, list]:
    """总页数上限 15（仅两类资料同时存在时生效，与旧行为一致）。"""
    if core_pages and ref_pages:
        core_limit = int(MAX_PAGES * core_ratio)
        ref_limit = MAX_PAGES - core_limit
        return core_pages[: max(1, core_limit)], ref_pages[: max(1, ref_limit)]
    return core_pages, ref_pages


def reinject_missing_images(markdown: str, tags: list[str]) -> tuple[str, int]:
    """AI 丢掉的图片标签补在本章末尾（带小标题），保证图不丢且不打断段落。"""
    missing = [t for t in tags if t not in markdown]
    if not missing:
        return markdown, 0
    block = "#### 📷 配图\n\n" + "\n\n".join(missing)
    return markdown.rstrip() + "\n\n" + block + "\n", len(missing)


def strip_ai_outros(markdown: str) -> str:
    markdown = re.sub(r"【结语】.*", "", markdown, flags=re.DOTALL)
    markdown = re.sub(r"## 🎓 结语.*", "", markdown, flags=re.DOTALL)
    markdown = re.sub(r"### 🎓 结语.*", "", markdown, flags=re.DOTALL)
    return markdown.strip()


def build_course_info(course: dict) -> CourseInfo:
    return CourseInfo(
        name=course["name"],
        school_level=course["school"],
        major=course["major"],
        is_core_major=course["is_major"],
        credits=course["credits"],
        days_left=course["days_left"],
        target_score=course["target_score"],
        user_difficulty=course["difficulty"],
    )


def chapter_blocks(chapter: Chapter, pages: list[str], per_call: int = PAGES_PER_CALL) -> list[tuple[str, list[str]]]:
    """把一章的页面打包成若干次请求：(正文, 该批次的图片标签)。"""
    texts = [pages[i] for i in chapter.pages if 0 <= i < len(pages)]
    blocks: list[tuple[str, list[str]]] = []
    for start in range(0, len(texts), per_call):
        batch = texts[start:start + per_call]
        content = "\n\n".join(batch)
        if not content.strip():
            continue
        tags = re.findall(r"\[\[\[IMAGE:.*?\]\]\]", content)
        blocks.append((content, tags))
    return blocks


def _neighbors(outline: Outline, index: int) -> str:
    parts = []
    if index > 0:
        parts.append(f"上一章《{outline.chapters[index - 1].title}》")
    if index + 1 < len(outline.chapters):
        parts.append(f"下一章《{outline.chapters[index + 1].title}》")
    return "；".join(parts) or "无"


def _default_outline_ai(system: str, user: str) -> str:
    return call_ai_with_retry(system, user, temp=0.1)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def run_guide(
    course: dict,
    *,
    mode: str = "full",
    persona: str = "温柔小姐姐",
    core_ratio: float = 0.8,
    lang: str = "中文",
    user_note: str = "",
    on_progress: ProgressCb = noop_progress,
    stop_event: threading.Event | None = None,
    outline: Outline | None = None,
    ai_call=None,
    guide_generator=None,
) -> RunResult | None:
    """生成一份讲义。被用户中断时返回 None。

    可注入 outline / ai_call / guide_generator，便于离线测试。
    """
    stop_event = stop_event or threading.Event()
    started = time.time()
    is_key = mode == "key"
    user_choice = "option_1_保命流" if is_key else "option_2_硬核流"

    db = get_db_session()
    try:
        materials = db.query(DBMaterial).filter(DBMaterial.course_id == course["id"]).all()
    finally:
        db.close()
    if not materials:
        raise RuntimeError("没有找到任何上传资料")

    material_meta = []
    for m in materials:
        try:
            stat = os.stat(m.file_path)
            size, mtime = stat.st_size, stat.st_mtime
        except OSError:
            size, mtime = 0, 0
        material_meta.append({"path": m.file_path, "size": size, "mtime": mtime})

    core_pages: list[str] = []
    ref_pages: list[str] = []
    for material in materials:
        if stop_event.is_set():
            return None
        on_progress(ProgressEvent(f"📖 正在解析文件: {material.filename}...", 0.08))
        def _parse_progress(done: int, total: int, stage: str = "caption",
                            _name: str = material.filename):
            label = "正在 OCR 扫描页" if stage == "ocr" else "正在识别配图"
            on_progress(ProgressEvent(
                f"🖼️ {label}：{_name}（{done}/{total}）",
                0.05 + 0.06 * (done / max(1, total))))

        pages = extract_text_from_file(material.file_path, on_progress=_parse_progress)
        (core_pages if material.file_type == "core" else ref_pages).extend(pages)

    weight_prompt = build_weight_prompt(core_pages, ref_pages, core_ratio)
    core_pages, ref_pages = truncate_pages(core_pages, ref_pages, core_ratio)
    pages = core_pages + ref_pages
    if not pages:
        raise RuntimeError("未从资料中解析到任何内容")

    if outline is None:
        cache_key = outline_store.fingerprint(material_meta, lang)
        outline = outline_store.load(cache_key)
        if outline is None:
            on_progress(ProgressEvent("🧭 正在规划课程大纲...", 0.12))
            outline = generate_outline(pages, course, lang=lang,
                                       ai_call=ai_call or _default_outline_ai)
            outline_store.save(cache_key, outline)
    if not outline.chapters:
        raise RuntimeError("无法规划章节结构")

    total = len(outline.chapters)
    on_progress(ProgressEvent(f"🧭 已规划 {total} 章，开始逐章生成...", 0.15))
    logger.info("讲义大纲来源={} 章节={}", outline.source, total)

    generator = guide_generator or generate_super_guide
    info = build_course_info(course)
    evaluation = info.evaluate()
    urgency_text = (f"紧迫度 {evaluation['final_priority_weight']:.0f}/100（{evaluation['status']}），"
                    f"建议每天 {evaluation['suggested_daily_hours']:g} 小时")
    chapter_mds: list[tuple[str, str]] = []
    images_expected = images_reinjected = 0
    empty_calls = 0

    # 先把所有块排成任务，再按并发度执行（保持章节顺序输出）
    jobs: list[tuple[int, int, str, list[str], dict]] = []
    tags_map: dict[tuple[int, int], list[str]] = {}
    for ci, chapter in enumerate(outline.chapters):
        target_words = max(700, min(2800, int(chapter.est_words * (0.6 if is_key else 1.0))))
        blocks = chapter_blocks(chapter, pages)
        for bi, (content, tags) in enumerate(blocks):
            context = {
                "title": chapter.title if bi == 0 else f"{chapter.title}（续）",
                "index": ci,
                "total": total,
                "must_know": chapter.must_know if bi == 0 else [],
                "neighbors": _neighbors(outline, ci),
                "target_words": max(400, target_words // max(1, len(blocks))),
                "urgency": urgency_text,
            }
            jobs.append((ci, bi, content, tags, context))
            tags_map[(ci, bi)] = tags
            images_expected += len(tags)

    results: dict[tuple[int, int], str] = {}
    total_jobs = len(jobs)
    done = 0
    retries = 0

    def _call(job):
        nonlocal retries
        ci, bi, content, tags, context = job
        if stop_event.is_set():
            return (ci, bi), ""
        markdown = ""
        for attempt in (1, 2):
            payload = content if attempt == 1 else content[: max(1500, len(content) // 2)]
            try:
                markdown = generator(f"【本章资料】\n{payload}", info, persona=persona,
                                     user_choice=user_choice, weight_prompt=weight_prompt, lang=lang,
                                     chapter=context, user_note=user_note)
            except Exception as exc:  # noqa: BLE001
                logger.error("第 {} 章第 {} 块生成异常: {}", ci + 1, bi + 1, exc)
                markdown = ""
            if markdown and len(markdown.strip()) >= 20 and "跳过" not in markdown:
                return (ci, bi), markdown
            if attempt == 1:
                retries += 1
                logger.warning("第 {} 章第 {} 块为空（疑似截断），缩短输入重试一次", ci + 1, bi + 1)
        return (ci, bi), ""

    def _report(key, markdown):
        nonlocal done
        done += 1
        if markdown:
            results[key] = markdown
        eta = int((time.time() - started) / max(1, done) * (total_jobs - done)) if done else None
        on_progress(ProgressEvent(f"🧠 已生成 {done}/{total_jobs} 个章节块", 
                                  0.15 + done / max(1, total_jobs) * 0.75, eta))

    workers = _concurrency()
    if workers > 1 and total_jobs > 1:
        logger.info("并发生成：{} 个任务 / 并发 {}", total_jobs, workers)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_call, job) for job in jobs]
            for future in as_completed(futures):
                key, markdown = future.result()
                _report(key, markdown)
                if stop_event.is_set():
                    break
    else:
        for job in jobs:
            if stop_event.is_set():
                return None
            key, markdown = _call(job)
            _report(key, markdown)

    if stop_event.is_set():
        return None

    grouped: dict[int, list[tuple[int, str]]] = {}
    for (ci, bi), markdown in results.items():
        grouped.setdefault(ci, []).append((bi, markdown))

    for ci, chapter in enumerate(outline.chapters):
        parts: list[str] = []
        for bi, markdown in sorted(grouped.get(ci, [])):
            if len(markdown.strip()) < 20 or "跳过" in markdown:
                empty_calls += 1
                logger.warning("第 {} 章第 {} 块未返回有效内容", ci + 1, bi + 1)
                continue
            if bi > 0:  # 同一章的续块，不再生成新的「## 第 N 章」
                markdown = re.sub(r"^##\s+", "### ", markdown, count=1, flags=re.MULTILINE)
            markdown, fixed = reinject_missing_images(markdown, tags_map.get((ci, bi), []))
            images_reinjected += fixed
            parts.append(strip_ai_outros(markdown))
        chapter_md = "\n\n".join(p for p in parts if p)
        if chapter_md:
            chapter_mds.append((chapter.title, chapter_md))

    if not chapter_mds:
        raise RuntimeError("未提取到有效考点（所有章节均生成失败）")

    on_progress(ProgressEvent("🎨 正在排版公式、图片与高亮名词...", 0.92))

    qa = check_chapters(chapter_mds, mode=mode, lang=lang)
    for issue in qa.issues:
        logger.warning("质量校验: {}", issue)

    final_markdown = "\n\n---\n\n".join(md for _, md in chapter_mds)
    outro_lang = "en" if lang == "English" else "zh"
    final_markdown += "\n\n---\n\n" + OUTROS[outro_lang].get(persona, OUTROS[outro_lang]["温柔小姐姐"])

    time_str = time.strftime("%m%d_%H%M", time.localtime())
    mode_str = "精简" if is_key else "全量"
    output_path = str(default_output_dir() / f"{course['name']}_{mode_str}_{time_str}.html")

    export_to_html(final_markdown, output_file=output_path, course=info, persona=persona,
                   doc_type="专属讲义", lang=lang)

    db = get_db_session()
    try:
        db.add(DBGeneratedFile(course_id=course["id"], file_path=output_path,
                               created_at=time_str, file_type="guide"))
        db.commit()
    finally:
        db.close()

    metrics = {
        "kind": "guide",
        "mode": mode,
        "persona": persona,
        "lang": lang,
        "core_ratio": core_ratio,
        "outline_source": outline.source,
        "outline_cached": outline.source == "cached",
        "chapters": total,
        "chapters_done": len(chapter_mds),
        "empty_calls": empty_calls,
        "retries": retries,
        "images_expected": images_expected,
        "images_reinjected": images_reinjected,
        "chars": len(final_markdown),
        "elapsed_s": round(time.time() - started, 1),
        "qa_ok": qa.ok,
        "qa_issues": qa.issues[:20],
        "qa_chapters": qa.metrics.get("chapters", []),
    }
    dump_debug("guide", final_markdown, metrics)

    on_progress(ProgressEvent("✅ 渲染完成，即将打开...", 1.0))
    time.sleep(0.5)

    return RunResult(output_path=output_path, doc_type="专属讲义",
                     markdown=final_markdown, metrics=metrics,
                     warnings=qa.issues[:20])
