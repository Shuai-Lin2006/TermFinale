"""讲义生成服务：解析资料 → 分块 → 调 AI → 渲染 HTML。

行为与重构前保持一致，唯一的变化：
1. 进度通过回调上报，不再直接操作控件；
2. 原始 Markdown 与指标落盘到 debug/；
3. AI 吞掉的图片标签统一补在本章末尾，不再插进段落中间。
"""
from __future__ import annotations

import re
import threading
import time

from loguru import logger

from core.ai_engine import generate_super_guide
from core.database import GeneratedFile as DBGeneratedFile, Material as DBMaterial, get_db_session
from core.exporter import export_to_html
from core.parser import extract_text_from_file
from core.personas import OUTROS
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
CHUNK_SIZE = 2


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


def build_chunks(pages: list, prefix_tag: str) -> list[tuple[str, str]]:
    chunks = []
    for i in range(0, len(pages), CHUNK_SIZE):
        content = "\n\n".join(pages[i:i + CHUNK_SIZE])
        if not content.strip():
            continue
        if i > 0 and len(pages[i - 1]) > 150:
            content = "【上一页回顾...】\n" + pages[i - 1][-150:] + "\n\n" + content
        chunks.append((prefix_tag, content))
    return chunks


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
    on_progress: ProgressCb = noop_progress,
    stop_event: threading.Event | None = None,
) -> RunResult | None:
    """生成一份讲义。被用户中断时返回 None。"""
    stop_event = stop_event or threading.Event()
    started = time.time()

    db = get_db_session()
    try:
        materials = db.query(DBMaterial).filter(DBMaterial.course_id == course["id"]).all()
    finally:
        db.close()
    if not materials:
        raise RuntimeError("没有找到任何上传资料")

    core_pages: list[str] = []
    ref_pages: list[str] = []
    for material in materials:
        if stop_event.is_set():
            return None
        on_progress(ProgressEvent(f"📖 正在解析文件: {material.filename}...", 0.1))
        pages = extract_text_from_file(material.file_path)
        (core_pages if material.file_type == "core" else ref_pages).extend(pages)

    weight_prompt = build_weight_prompt(core_pages, ref_pages, core_ratio)
    core_pages, ref_pages = truncate_pages(core_pages, ref_pages, core_ratio)

    chunks = build_chunks(core_pages, "【核心重点】") + build_chunks(ref_pages, "【参考资料】")
    if not chunks:
        raise RuntimeError("未从资料中解析到任何文本内容")

    info = build_course_info(course)
    total = len(chunks)
    results: list[str] = []
    images_seen = 0
    images_reinjected = 0
    empty_chunks = 0

    for i, (tag, content) in enumerate(chunks):
        if stop_event.is_set():
            return None

        eta = None
        if i > 0:
            avg = (time.time() - started) / i
            eta = int(avg * (total - i))

        on_progress(ProgressEvent(
            f"🧠 AI导师正在梳理考点... ({i + 1}/{total})",
            0.1 + (i / total) * 0.8,
            eta,
        ))

        img_tags = re.findall(r"\[\[\[IMAGE:.*?\]\]\]", content)
        images_seen += len(img_tags)

        user_choice = "option_1_保命流" if mode == "key" else "option_2_硬核流"
        markdown = generate_super_guide(
            f"{tag}\n{content}", info, persona=persona, user_choice=user_choice,
            weight_prompt=weight_prompt, lang=lang,
        )

        if markdown and "跳过" not in markdown and len(markdown.strip()) > 20:
            markdown, fixed = reinject_missing_images(markdown, img_tags)
            images_reinjected += fixed
            results.append(strip_ai_outros(markdown))
        else:
            empty_chunks += 1
            logger.warning("第 {}/{} 块未返回有效内容（疑似截断或跳过）", i + 1, total)

    if not results:
        raise RuntimeError("未提取到有效考点")

    on_progress(ProgressEvent("🎨 正在排版公式、图片与高亮名词...", 0.9))

    final_markdown = "\n\n---\n\n".join(results)
    outro_lang = "en" if lang == "English" else "zh"
    final_markdown += "\n\n---\n\n" + OUTROS[outro_lang].get(persona, OUTROS[outro_lang]["温柔小姐姐"])

    time_str = time.strftime("%m%d_%H%M", time.localtime())
    mode_str = "精简" if mode == "key" else "全量"
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
        "chunks": total,
        "core_pages": len(core_pages),
        "ref_pages": len(ref_pages),
        "empty_chunks": empty_chunks,
        "images_expected": images_seen,
        "images_reinjected": images_reinjected,
        "chars": len(final_markdown),
        "elapsed_s": round(time.time() - started, 1),
    }
    dump_debug("guide", final_markdown, metrics)

    on_progress(ProgressEvent("✅ 渲染完成，即将打开...", 1.0))
    time.sleep(0.5)

    return RunResult(output_path=output_path, doc_type="专属讲义",
                     markdown=final_markdown, metrics=metrics)
