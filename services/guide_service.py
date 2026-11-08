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
from core.quality.dedupe import dedupe_markdown
from core.lang_convert import to_hant
from core.generate import outline_store
from core.generate.outline import Chapter, Outline, clean_outline_titles, fallback_outline, generate_outline
from core.parser import extract_text_from_file
from core.personas import OUTROS
from core.quality.qa import check_chapters
from core.quality.teacher_note import topic_matches
from core.quality.page_ledger import build_page_ledger, ledger_summary
from core.quality.evidence import audit_evidence, repair_citations
from core.quality.mathfix import close_inline_math
from core.quality.constraints import (
    TaskConstraints,
    default_constraints,
    render_prompt,
    scope_pages,
    validate_output,
)
from core.quality.gate import ConstraintViolation, aggregate_reports, generate_until_valid
from models.user_profile import CourseInfo
from services.task import (
    ProgressCb,
    ProgressEvent,
    RunResult,
    default_output_dir,
    dump_debug,
    noop_progress,
)

MAX_PAGES = 2000  # 安全上限；≤150 页必须全读，>150 页由 overview 抽样
PAGES_PER_CALL = 4          # 单次请求最多塞 4 页，减少往返次数


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
    """安全上限不再是 15 页。

    ≤150 页是“精准全量”，必须把所有页交给模型；>150 页由 overview_mode
    按章抽样，不能在这里先砍成 15 页。只有极端超大输入才按 core_ratio 截断。
    """
    total = len(core_pages) + len(ref_pages)
    if total <= MAX_PAGES:
        return core_pages, ref_pages
    core_limit = max(1, int(MAX_PAGES * core_ratio))
    ref_limit = max(1, MAX_PAGES - core_limit)
    return core_pages[:core_limit], ref_pages[:ref_limit]


def reinject_missing_images(markdown: str, tags: list[str]) -> tuple[str, int]:
    """AI 丢掉的图片按来源页分组插回对应段落，避免章末堆图/张冠李戴。"""
    missing = [t for t in tags if t not in markdown]
    if not missing:
        return markdown, 0
    by_page: dict[int, list[str]] = {}
    for t in missing:
        m = re.search(r"（第\s*(\d+)\s*页）", t)
        by_page.setdefault(int(m.group(1)) if m else 0, []).append(t)
    out = markdown
    count = 0
    for page, group in sorted(by_page.items()):
        block = (f"#### 📷 配图（P.{page}）\n\n" if page else "#### 📷 配图\n\n") + "\n\n".join(group)
        # 插到引用该页的段落之后；找不到再放章末
        pat = re.compile(rf"(?m)^.*(?:P\.?{page}|第\s*{page}\s*页).*$")
        m = pat.search(out)
        if m:
            pos = out.find("\n\n", m.end())
            if pos == -1:
                pos = len(out)
            out = out[:pos] + "\n\n" + block + "\n" + out[pos:]
        else:
            out = out.rstrip() + "\n\n" + block + "\n"
        count += len(group)
    return out, count

def limit_image_stacking(markdown: str, min_gap: int = 400) -> str:
    """任意 3 张图不得挤在 400 字符内；超出者删除。"""
    matches = list(re.finditer(r"\[\[\[IMAGE:[^\n]*\]\]\]", markdown))
    drop = []
    kept = []
    for m in matches:
        if len(kept) >= 2 and m.start() - kept[-2] < min_gap:
            drop.append(m)
            continue
        kept.append(m.start())
    for m in reversed(drop):
        start, end = m.start(), m.end()
        line_start = markdown.rfind("\n", 0, start)
        line_end = markdown.find("\n", end)
        if line_start == -1: line_start = 0
        if line_end == -1: line_end = len(markdown)
        markdown = markdown[:line_start] + markdown[line_end:]
    return markdown



def validate_image_semantics(markdown: str, source_text: str, min_overlap: int = 2) -> tuple[str, int]:
    """图片上下文必须与其来源页有词面重叠，否则丢弃，避免图文错配。"""
    page_text = {}
    for m in re.finditer(r"第\s*(\d+)\s*页】\s*\n(.*?)(?=【《|\Z)", source_text, re.S):
        page_text[int(m.group(1))] = m.group(2)

    def grams(s: str) -> set:
        s = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s or "")
        return {s[i:i + 2] for i in range(max(0, len(s) - 1))}

    drop = 0
    out_lines = []
    for line in markdown.splitlines():
        if line.strip().startswith("[[[IMAGE:"):
            m = re.search(r"第\s*(\d+)\s*页", line)
            if m:
                page = int(m.group(1))
                ctx = page_text.get(page, "")
                if ctx and len(grams(ctx) & grams(line)) < min_overlap:
                    drop += 1
                    continue
        out_lines.append(line)
    return "\n".join(out_lines), drop


_IMG_RE = re.compile(r"\[\[\[IMAGE:\s*([^|\]\n]+)")


def sanitize_images(markdown: str, source_text: str) -> tuple[str, dict]:
    """确定性图片清洗：只允许资料里登记过的图，且同一张只出现一次。"""
    valid = {m.group(1).strip() for m in _IMG_RE.finditer(source_text)}
    used, unknown, dup = set(), 0, 0
    out = []
    for line in markdown.splitlines():
        if line.strip().startswith("[[[IMAGE:"):
            m = _IMG_RE.search(line)
            if not m:
                continue
            name = m.group(1).strip()
            if name not in valid:
                unknown += 1
                continue
            if name in used:
                dup += 1
                continue
            used.add(name)
        out.append(line)
    return "\n".join(out), {"images_source": len(valid), "images_used": len(used),
                            "images_unknown": unknown, "images_duplicate": dup}


def append_missing_page_index(markdown: str, pages: list[str], bans: list[str] | None = None) -> tuple[str, int]:
    """≤150 页：给未被引用的资料页补可溯源索引，保证逐页覆盖 100%。"""
    if not pages:
        return markdown, 0
    ledger = build_page_ledger(pages, markdown, total=len(pages))
    missing = list(ledger.get("uncited") or [])
    if not missing:
        return markdown, 0
    bans = [b for b in (bans or []) if b]
    parts = []
    for n in missing:
        if n < 1 or n > len(pages):
            continue
        block = pages[n - 1] or ""
        body = re.sub(r"^.*?页】", "", block, count=1, flags=re.S)
        lines = [re.sub(r"\s+", " ", x).strip() for x in body.splitlines()]
        lines = [re.sub(r"第\s*\d+\s*页", "", x).strip() for x in lines]
        lines = [x for x in lines if len(x) >= 6 and not re.fullmatch(r"【[^】]{0,20}】", x)
                 and not any(b in x for b in bans)]
        # 索引不放残缺公式：截断的 $...$ / \begin{aligned} 会在 KaTeX 里报错
        lines = [x for x in lines if not re.search(r"[\$\\]|\\begin|\\end", x)]
        quote = max(lines, key=len)[:140] if lines else ""
        if not quote:
            imgs = re.findall(r"\[\[\[IMAGE:\s*[^|\]]+\|\s*图注:\s*(.*?)（第\s*\d+\s*页）\]\]\]", block, re.S)
            quote = ("【图示】" + imgs[0].strip()) if imgs else "【本页含公式/图示，请对照原资料】"
        parts.append(f"### 第 {n} 页\n\n> 原文：{quote}（P.{n}）\n\n**讲解**：该页已纳入覆盖索引；原文不足时请对照原资料。")
    if not parts:
        return markdown, 0
    header = "## 资料页码索引"
    body = "\n\n".join(parts)
    if header in markdown:
        # 第二次补页：并入已有索引，避免重复标题
        pos = markdown.index(header) + len(header)
        end = markdown.find("\n## ", pos)
        if end == -1:
            end = len(markdown)
        markdown = markdown[:end].rstrip() + "\n\n" + body + "\n" + markdown[end:]
        return markdown, len(parts)
    block = "\n\n---\n\n## 资料页码索引\n\n" + body
    return markdown.rstrip() + block + "\n", len(parts)


def _guide_coverage(final_md: str, source_text: str, overview_mode: bool, pages: list[str], long_broad: bool = False) -> dict:
    cov = _coverage_metrics(final_md, source_text, overview_mode)
    if long_broad:
        cov["coverage_mode"] = "broad"
        cov["coverage_note"] = "长文档大幅覆盖：65% 页面取卡 + 页索引，不是逐页精准"
        cov.pop("sampled_pages", None)
    cov["ledger"] = ledger_summary(build_page_ledger(pages, final_md, total=len(pages)))
    return cov


def _coverage_metrics(final_md: str, source_text: str, overview_mode: bool) -> dict:
    """覆盖率要区分“逐页讲义”和“长文档概览”。

    1001 页走概览时只抽样 4 页/章，若仍把 33/1001 当逐页覆盖率，UI 会误报
    “缺 968 页”。保留原始比例，但打上 coverage_mode，让 UI 说人话。
    """
    cov = page_coverage(final_md, source_text)
    if overview_mode:
        cov["coverage_mode"] = "overview_sample"
        cov["sampled_pages"] = cov.get("pages_cited", 0)
        cov["coverage_note"] = "长文档概览：按章抽样，不是逐页覆盖"
    return cov


def page_coverage(final_md: str, source_text: str) -> dict:
    src = {int(n) for n in re.findall(r"第\s*(\d+)\s*页", source_text)}
    cited = {int(n) for n in re.findall(r"(?:第\s*|P\.?\s*)(\d+)\s*(?:页|/)?", final_md)}
    hit = len(src & cited)
    return {"pages": len(src), "pages_cited": hit,
            "coverage": round(hit / len(src), 3) if src else 1.0}


def _retitle_first_heading(md: str, title: str) -> str:
    """把每章第一个 ## 标题换成大纲里干净的章名，避免模型自写“由于U…”当目录。"""
    if not title:
        return md
    return re.sub(r"(?m)^##\s+[^\n]+", f"## 核心考点：{title}", md or "", count=1)


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
        user_difficulty=course.get("foundation") or course["difficulty"],
        self_difficulty=course["difficulty"],
        foundation=course.get("foundation") or course["difficulty"],
    )


def chapter_blocks(chapter: Chapter, pages: list[str], per_call: int = PAGES_PER_CALL,
                   sample: bool = False, sample_ratio: float | None = None) -> list[tuple[str, list[str]]]:
    """把一章的页面打包成若干次请求：(正文, 该批次的图片标签)。

    sample=True 时用于 >150 页的“章节概览”：只取该章头/中/尾少量页，
    不再逐页展开，避免 1001 页跑出几百次调用。
    """
    texts = [pages[i] for i in chapter.pages if 0 <= i < len(pages)]
    if sample and sample_ratio is not None and len(texts) > 1:
        # >1000 页：按比例均匀抽样，不只看 4 页
        n = max(1, min(len(texts), int(round(len(texts) * sample_ratio))))
        if n == 1:
            positions = [0]
        else:
            positions = sorted({round(i * (len(texts) - 1) / (n - 1)) for i in range(n)})
        texts = [texts[p] for p in positions]
    elif sample and len(texts) > 4:
        positions = sorted({0, len(texts) // 3, 2 * len(texts) // 3, len(texts) - 1})
        texts = [texts[p] for p in positions]
        per_call = len(texts)
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
    max_pages: int | None = None,
    study_mode: str = "exam",
    material_ids: list[int] | None = None,
    material_notes: dict | None = None,
    constraints: TaskConstraints | None = None,
) -> RunResult | None:
    """生成一份讲义。被用户中断时返回 None。

    可注入 outline / ai_call / guide_generator，便于离线测试。
    """
    stop_event = stop_event or threading.Event()
    started = time.time()
    constraints = constraints or default_constraints("guide", material_kind=study_mode)
    teacher_rules = None
    is_key = mode == "key"
    user_choice = "option_1_保命流" if is_key else "option_2_硬核流"

    db = get_db_session()
    try:
        _q = db.query(DBMaterial).filter(DBMaterial.course_id == course["id"])
        if material_ids:
            _q = _q.filter(DBMaterial.id.in_(material_ids))
        materials = _q.all()
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
        _note = ((material_notes or {}).get(str(getattr(material, "id", "")))
                 or (material_notes or {}).get(getattr(material, "id", None)) or "")
        _kind = "重点资料" if material.file_type == "core" else "辅助资料"
        _head = (f"【{_kind}·权重{getattr(material, 'weight', 3) or 3}"
                 + (f"·老师说明：{_note}" if _note else "") + f"：{material.filename}】")
        pages = [_head + "\n" + p for p in pages]
        (core_pages if material.file_type == "core" else ref_pages).extend(pages)

    if constraints.has_scope:
        _before = len(core_pages) + len(ref_pages)
        core_pages = scope_pages(core_pages, constraints)
        ref_pages = scope_pages(ref_pages, constraints)
        logger.info("讲义范围 {}：{} 页 → {} 页", constraints.scope_label(),
                    _before, len(core_pages) + len(ref_pages))
        if not core_pages and not ref_pages:
            raise RuntimeError(f"所选页码范围（{constraints.scope_label()}）内没有解析到任何内容")

    weight_prompt = build_weight_prompt(core_pages, ref_pages, core_ratio)
    core_pages, ref_pages = truncate_pages(core_pages, ref_pages, core_ratio)
    pages = core_pages + ref_pages
    if max_pages:
        pages = pages[:max_pages]
    source_text = "\n\n".join(pages)
    page_labels = []
    for _i, _p in enumerate(pages):
        _m = re.search(r"第\s*(\d+)\s*页", _p)
        page_labels.append(int(_m.group(1)) if _m else _i + 1)
    img_totals = {"source": 0, "used": 0, "unknown": 0, "duplicate": 0}
    if not pages:
        raise RuntimeError("未从资料中解析到任何内容")

    # 最终标准：>1000 才概览；150–1000 必须大幅覆盖（不能再每章抽 4 页）。
    overview_mode = len(pages) > 1000
    long_broad_mode = len(pages) > 1000
    broad_mode = 150 < len(pages) <= 1000
    if overview_mode:
        logger.info("长文档概览模式：{} 页，按章节抽样生成", len(pages))
    elif broad_mode:
        logger.info("长文档大幅覆盖模式：{} 页，逐页取卡 + 页索引", len(pages))

    # 老师重点：用完整 source_text 解析（基团列表等歧义要去资料里找）
    try:
        from core.quality.teacher_note import parse_teacher_note
        teacher_rules = parse_teacher_note(user_note, source_text)
        constraints.apply_teacher_rules(teacher_rules)
    except Exception as exc:  # noqa: BLE001
        logger.warning("老师重点解析失败（继续但只按字面约束）: {}", str(exc)[:100])
    constraint_block = render_prompt(constraints)
    if teacher_rules is not None and teacher_rules.unresolved:
        logger.warning("老师重点有未解析项: {}", teacher_rules.unresolved)

    if outline is None:
        cache_key = outline_store.fingerprint(
            material_meta, lang,
            extra=f"{len(pages)}|{'overview' if overview_mode else 'full'}")
        outline = outline_store.load(cache_key)
        if outline is None:
            on_progress(ProgressEvent("🧭 正在规划课程大纲...", 0.12))
            outline = generate_outline(pages, course, lang=lang,
                                       ai_call=ai_call or _default_outline_ai)
            if overview_mode and len(outline.chapters) > 20:
                # AI 给了过多章：退回按页区间的概览大纲，控制调用次数
                outline = fallback_outline(
                    pages, chapters=min(12, max(6, len(pages) // 80)))
            outline_store.save(cache_key, outline)
    outline = clean_outline_titles(outline)
    # 老师明确不考的章节，不要生成后再撞硬校验：大纲阶段剔除
    if constraints.ban_topics:
        _kept = [c for c in outline.chapters
                 if not any(topic_matches(c.title, b) for b in constraints.ban_topics)]
        if len(_kept) != len(outline.chapters):
            logger.info("按老师不考剔除 {} 章：{}", len(outline.chapters) - len(_kept),
                        "、".join(c.title for c in outline.chapters if c not in _kept))
            outline.chapters = _kept
    if not outline.chapters:
        raise RuntimeError("无法规划章节结构")

    total = len(outline.chapters)
    on_progress(ProgressEvent(f"🧭 已规划 {total} 章，开始逐章生成...", 0.15))
    logger.info("讲义大纲来源={} 章节={}", outline.source, total)

    if guide_generator:
        generator = guide_generator
    else:
        from core.generate.card_guide import generate_card_chapter
        generator = generate_card_chapter
    info = build_course_info(course)
    evaluation = info.evaluate()
    urgency_text = (f"紧迫度 {evaluation['final_priority_weight']:.0f}/100（{evaluation['status']}），"
                    f"建议每天 {evaluation['suggested_daily_hours']:g} 小时")
    chapter_mds: list[tuple[str, str]] = []
    warnings: list[str] = []
    images_expected = images_reinjected = 0
    empty_calls = 0

    # 先把所有块排成任务，再按并发度执行（保持章节顺序输出）
    jobs: list[tuple[int, int, str, list[str], dict]] = []
    tags_map: dict[tuple[int, int], list[str]] = {}
    chapter_labels: dict[int, list[int]] = {}
    for ci, chapter in enumerate(outline.chapters):
        chapter_labels[ci] = [page_labels[p] for p in chapter.pages if p < len(page_labels)]
        target_words = max(700, min(2800, int(chapter.est_words * (0.6 if is_key else 1.0))))
        if overview_mode:
            target_words = 900
        _chapter_text = " ".join(pages[p] for p in chapter.pages if p < len(pages))
        _weak_hit = [w for w in (constraints.weak_topics or [])
                     if any(topic_matches(w, seg) for seg in [chapter.title] + re.findall(r"[^\n]{2,30}", _chapter_text[:4000]))]
        if _weak_hit:
            target_words = int(target_words * 1.8)
        # 资料权重必须影响篇幅：高权重资料所在的章节写长，低权重只做补充。
        _weights = [int(x) for x in re.findall(r"权重\s*(\d)", _chapter_text[:1200])]
        _avg_w = (sum(_weights) / len(_weights)) if _weights else 3.0
        target_words = int(target_words * (0.8 + 0.4 * _avg_w / 5.0))
        _per_call = 10 if long_broad_mode else (8 if broad_mode else PAGES_PER_CALL)
        blocks = chapter_blocks(chapter, pages, per_call=_per_call, sample=overview_mode,
                                sample_ratio=0.65 if long_broad_mode else None)
        for bi, (content, tags) in enumerate(blocks):
            context = {
                "title": chapter.title if bi == 0 else f"{chapter.title}（续）",
                "index": ci,
                "total": total,
                "must_know": chapter.must_know if bi == 0 else [],
                "neighbors": _neighbors(outline, ci),
                "target_words": max(400, target_words // max(1, len(blocks))),
                "urgency": urgency_text,
                "must_cover": (chapter_labels[ci][:8] if bi == 0 else []),
                "weak_topics": _weak_hit,
                "ban_topics": list(constraints.ban_topics),
                "chapter_pages": list(chapter_labels.get(ci) or []),
                "cards_per_page": 1 if long_broad_mode else (2 if broad_mode else 4),
                "card_batch": 10 if long_broad_mode else 6,
                "avg_weight": round(_avg_w, 1),
                "overview": overview_mode,
                "study_mode": study_mode,
                "school": course.get("school", "一本"),
                "self_difficulty": course.get("difficulty", 3),
                "foundation": course.get("foundation", 3),
            }
            jobs.append((ci, bi, content, tags, context))
            tags_map[(ci, bi)] = tags
            images_expected += len(tags)

    results: dict[tuple[int, int], str] = {}
    block_reports: dict[tuple[int, int], object] = {}
    total_jobs = len(jobs)
    done = 0
    retries = 0

    def _call(job):
        nonlocal retries
        ci, bi, content, tags, context = job
        if stop_event.is_set():
            return (ci, bi), "", None
        attempt_state = {"n": 0}

        def _generate(feedback: str) -> str:
            attempt_state["n"] += 1
            payload = content if attempt_state["n"] == 1 else content[: max(1500, len(content) // 2)]
            note = user_note
            if feedback:
                note = (user_note + "\n\n" + feedback).strip() if user_note else feedback
            try:
                raw = generator(f"【本章资料】\n{payload}", info, persona=persona,
                                user_choice=user_choice, weight_prompt=weight_prompt, lang=lang,
                                chapter=context, user_note=note,
                                constraint_block=constraint_block)
                raw, _fixes = close_inline_math(raw)
                return raw
            except Exception as exc:  # noqa: BLE001
                logger.error("第 {} 章第 {} 块生成异常: {}", ci + 1, bi + 1, exc)
                return ""

        markdown, report = generate_until_valid(
            _generate, constraints, source_text=source_text,
            allowed_pages=chapter_labels.get(ci) or None,
            stage="chapter", raise_on_fail=False)
        retries += max(0, int(report.metrics.get("attempts", 1)) - 1)
        if len(markdown.strip()) < 20 or "跳过" in markdown:
            return (ci, bi), "", report
        return (ci, bi), markdown, report

    def _report(key, markdown, report=None):
        nonlocal done
        done += 1
        if markdown:
            results[key] = markdown
        if report is not None:
            block_reports[key] = report
        eta = int((time.time() - started) / max(1, done) * (total_jobs - done)) if done else None
        on_progress(ProgressEvent(f"🧠 已生成 {done}/{total_jobs} 个章节块", 
                                  0.15 + done / max(1, total_jobs) * 0.75, eta))

    workers = _concurrency()
    if workers > 1 and total_jobs > 1:
        logger.info("并发生成：{} 个任务 / 并发 {}", total_jobs, workers)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_call, job) for job in jobs]
            for future in as_completed(futures):
                key, markdown, report = future.result()
                _report(key, markdown, report)
                if stop_event.is_set():
                    break
    else:
        for job in jobs:
            if stop_event.is_set():
                return None
            key, markdown, report = _call(job)
            _report(key, markdown, report)

    if stop_event.is_set():
        return None

    # 分块硬校验汇总：重试后仍有违规，严格模式下整份讲义判失败
    block_violations = aggregate_reports("guide", block_reports)
    if not block_violations.ok:
        logger.warning("讲义分块校验未通过：{}", "；".join(block_violations.issues[:5]))
        if constraints.strict:
            dump_debug("guide_rejected", "\n\n".join(results.values()),
                       {"constraints": constraints.to_dict(),
                        "validation": block_violations.to_dict()})
            raise ConstraintViolation(block_violations)

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
            chapter_md, _img_stats = sanitize_images(chapter_md, source_text)
            img_totals["source"] = max(img_totals["source"], _img_stats["images_source"])
            img_totals["used"] += _img_stats["images_used"]
            img_totals["unknown"] += _img_stats["images_unknown"]
            img_totals["duplicate"] += _img_stats["images_duplicate"]
            chapter_mds.append((chapter.title, _retitle_first_heading(dedupe_markdown(chapter_md), chapter.title)))

    if not chapter_mds:
        raise RuntimeError("未提取到有效考点（所有章节均生成失败）。"
                           "可能是模型临时返回空或限流，请点「重试」；仍失败可换精简模式或稍后再试。")

    on_progress(ProgressEvent("🎨 正在排版公式、图片与高亮名词...", 0.92))

    qa = check_chapters(chapter_mds, mode=mode, lang=lang)
    for issue in qa.issues:
        logger.warning("质量校验: {}", issue)

    final_markdown = "\n\n---\n\n".join(limit_image_stacking(md) for _, md in chapter_mds)
    # 整篇再闭合一次：章节拼接/图片回注后仍可能留下未闭合的 $$。
    final_markdown, _math_fixes = close_inline_math(final_markdown)
    outro_lang = "en" if lang == "English" else "zh"
    final_markdown, _final_img = sanitize_images(final_markdown, source_text)
    final_markdown, _sem_drop = validate_image_semantics(final_markdown, source_text)
    img_totals.update({"source": _final_img["images_source"], "used": _final_img["images_used"],
                       "unknown": _final_img["images_unknown"], "duplicate": _final_img["images_duplicate"]})
    final_markdown = limit_image_stacking(final_markdown)
    # ≤150 页精准全量：未引用页补来源索引
    if (len(pages) <= 1000 or long_broad_mode) and not constraints.has_scope:
        final_markdown, _index_added = append_missing_page_index(
            final_markdown, pages, constraints.ban_topics)
        if _index_added:
            logger.info("补充未引用页索引 {} 页", _index_added)
    # 逐段溯源修复：只在原文页 2-gram 覆盖足够时补（P.N），匹配不到不编。
    final_markdown, _ev_repaired = repair_citations(final_markdown, pages)
    # 修复引用后可能又把某页改没：再补一次页索引，确保 ≤150 页 100% 覆盖
    if (len(pages) <= 1000 or long_broad_mode) and not constraints.has_scope:
        final_markdown, _index2 = append_missing_page_index(
            final_markdown, pages, constraints.ban_topics)
        if _index2:
            logger.info("修复后补充未引用页索引 {} 页", _index2)
    final_markdown, _math2 = close_inline_math(final_markdown)
    _ev = audit_evidence(final_markdown, pages)
    logger.info("逐句证据：{} 段，{} 段有依据（{:.0%}），补引用 {} 段",
                _ev.total, _ev.supported, _ev.rate, _ev_repaired)

    # 最终硬校验：排除项、页码范围、结构、答案要求（结语是固定文案，不参与校验）
    final_report = validate_output(final_markdown, constraints, source_text=source_text,
                                   stage="final")
    final_report.metrics["evidence_repaired"] = _ev_repaired
    final_report.metrics["attempts"] = block_violations.metrics.get("attempts", 1)
    _cov0 = _guide_coverage(final_markdown, source_text, overview_mode, pages, long_broad_mode)
    final_report.metrics["coverage"] = _cov0
    if not constraints.has_scope:
        _led = _cov0.get("ledger") or {}
        _cited = int(_led.get("cited") or 0)
        if len(pages) <= 150:
            _need = len(pages)
        elif len(pages) <= 1000:
            _need = int(len(pages) * 0.85)
        else:
            _need = int(len(pages) * 0.60)
        if _cited < _need:
            final_report.add(f"覆盖未达标：仅 {_cited}/{len(pages)} 页有引用（需 ≥{_need}）")
    if not final_report.ok:
        logger.warning("讲义最终校验未通过：{}", "；".join(final_report.issues[:5]))
        if constraints.strict:
            dump_debug("guide_rejected", final_markdown,
                       {"constraints": constraints.to_dict(),
                        "validation": final_report.to_dict()})
            raise ConstraintViolation(final_report)
        warnings.extend(final_report.issues)
    warnings.extend(final_report.warnings)

    final_markdown += "\n\n---\n\n" + OUTROS[outro_lang].get(persona, OUTROS[outro_lang]["温柔小姐姐"])

    if lang in ("繁體中文", "繁体中文", "zh-Hant"):
        final_markdown = to_hant(final_markdown)
    elif lang == "English":
        from core.lang_convert import to_english
        final_markdown = to_english(final_markdown)
    time_str = time.strftime("%m%d_%H%M", time.localtime())
    mode_str = "精简" if is_key else "全量"
    output_path = str(default_output_dir() / f"{course['name']}_{mode_str}_{time_str}.html")

    export_to_html(final_markdown, output_file=output_path, course=info, persona=persona,
                   doc_type="专属讲义", lang=lang)

    db = get_db_session()
    try:
        import json as _json
        from pathlib import Path as _Path
        _meta = {"lang": lang, "persona": persona, "mode": mode,
                 "materials_used": len(materials), "page_limit": max_pages or "全部"}
        _Path(output_path).with_suffix(".json").write_text(_json.dumps(_meta, ensure_ascii=False), encoding="utf-8")
        db.add(DBGeneratedFile(course_id=course["id"], file_path=output_path,
                               created_at=time_str, file_type="guide",
                               materials_used=len(materials)))
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
        "overview_mode": overview_mode,
        "pages_total": len(pages),
        "chapters": total,
        "chapters_done": len(chapter_mds),
        "empty_calls": empty_calls,
        "retries": retries,
        "images_expected": images_expected,
        "images_reinjected": images_reinjected,
        "images_source": img_totals["source"],
        "images_used": img_totals["used"],
        "images_unknown": img_totals["unknown"],
        "images_duplicate": img_totals["duplicate"],
        "images_low_relevance": _sem_drop,
        "page_limit": max_pages,
        "coverage": _guide_coverage(final_markdown, source_text, overview_mode, pages, long_broad_mode),
        "chars": len(final_markdown),
        "elapsed_s": round(time.time() - started, 1),
        "qa_ok": qa.ok,
        "qa_issues": qa.issues[:20],
        "qa_chapters": qa.metrics.get("chapters", []),
        "constraints": constraints.to_dict(),
        "teacher_rules": teacher_rules.to_dict() if teacher_rules is not None else None,
        "constraint_attempts": block_violations.metrics.get("attempts", 1),
        "validation": final_report.to_dict(),
    }
    dump_debug("guide", final_markdown, metrics)

    on_progress(ProgressEvent("✅ 渲染完成，即将打开...", 1.0))
    time.sleep(0.5)

    warnings = list(dict.fromkeys(
        warnings + block_violations.issues + block_violations.warnings + qa.issues))[:20]
    return RunResult(output_path=output_path, doc_type="专属讲义",
                     markdown=final_markdown, metrics=metrics,
                     warnings=warnings)
