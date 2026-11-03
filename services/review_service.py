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
from core.generate.exam_builder import build_blueprint, validate_paper
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


def pack_pages(pages: list[str], limit: int = EXTRACT_CHUNK) -> list[str]:
    """把页装进不超过 limit 的块，整页为单位，不切断图标签。"""
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for page in pages:
        if buf and size + len(page) > limit:
            chunks.append("\n\n".join(buf))
            buf, size = [], 0
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
                 started: float) -> tuple[str, dict]:
    pages = split_pages(text)
    chunks = pack_pages(pages) if pages else []
    results: list[str] = []
    ok_chunks = 0

    for i, chunk in enumerate(chunks):
        if stop_event.is_set():
            break
        eta = int((time.time() - started) / i * (len(chunks) - i)) if i > 0 else None
        on_progress(ProgressEvent(
            f"🔍 正在提取区块 {i + 1}/{len(chunks)}（每块约 3 页）...",
            (i + 1) / max(1, len(chunks)), eta))
        markdown = generate_extraction(chunk, extract_type, with_answer)
        if markdown:
            markdown = re.sub(r"以下是.*?考题。", "", markdown)
            markdown = re.sub(r"以下是.*?提取.*?：", "", markdown)
            results.append(markdown)
            ok_chunks += 1

    merged, removed = dedupe_markdown("\n\n".join(results))
    coverage = {
        "pages": len(pages),
        "chunks": len(chunks),
        "chunks_ok": ok_chunks,
        "duplicates_removed": removed,
        "coverage": round(ok_chunks / len(chunks), 3) if chunks else 0.0,
    }
    logger.info("提取完成：{} 页 / {} 块 / 去重 {} 块", len(pages), len(chunks), removed)
    return merged, coverage


QUESTION_START = re.compile(r"^\s*(?:\*\*)?(\d{1,2})(?:\*\*)?\s*[.、．)）]\s*", re.MULTILINE)


def normalize_questions(markdown: str, blank: bool = False, height: int = 150) -> str:
    """统一题号：按出现顺序重排为 1..N（避免分块重复/列表被打断），可选每题留白。

    Markdown 的有序列表遇到留白会重新从 1 开始编号，这是题号错乱的根因；
    这里把题号改成普通加粗文字，编号完全由代码控制。
    """
    text = markdown or ""
    if not QUESTION_START.search(text):
        return text

    marker = f"[[BLANK:{height}]]"
    parts = re.split(r"(?m)^(?=\s*(?:\*\*)?\d{1,2}(?:\*\*)?\s*[.、．)）])", text)
    out: list[str] = []
    number = 0
    for part in parts:
        if not part.strip():
            continue
        if QUESTION_START.match(part):
            number += 1
            part = QUESTION_START.sub(f"**{number}.** ", part, count=1)
            if blank:
                part = part.rstrip() + "\n\n" + marker
        out.append(part.rstrip())
    return "\n\n".join(out)


def add_answer_space(markdown: str, height: int = 150) -> str:
    return normalize_questions(markdown, blank=True, height=height)


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
    lang: str = "中文",
    on_progress: ProgressCb = noop_progress,
    stop_event: threading.Event | None = None,
) -> RunResult | None:
    """task_type: analysis / extract / exam。被中断时返回 None。"""
    stop_event = stop_event or threading.Event()
    started = time.time()
    info = build_course_info(course)
    extra_metrics: dict = {}
    warnings: list[str] = []

    if task_type == "extract":
        markdown, coverage = _run_extract(
            text, extract_type, with_answer, on_progress, stop_event, started)
        if stop_event.is_set():
            return None
        doc_name = "练习卷" if (extract_type == "questions" and not with_answer) else "资料提取"
        if extract_type == "questions":
            # 题号统一由代码重排，避免跨块重复与列表被打断
            markdown = normalize_questions(markdown, blank=not with_answer)
        extra_metrics["coverage"] = coverage
        if coverage["coverage"] < 1.0:
            warnings.append(
                f"有 {coverage['chunks'] - coverage['chunks_ok']} 个区块没有产出，可能漏内容")

    elif task_type == "analysis":
        on_progress(ProgressEvent("🧠 AI 正在构建知识地图与因果链...", 0.4))
        if mode == "bundle":
            markdown = generate_logic_bundle(text, lang)
            doc_name = "逻辑分析"
        else:  # 兼容旧调用
            markdown = generate_logic_analysis(text, mode)
            doc_name = "逻辑分析" if mode == "text_logic" else "思维导图"
        if stop_event.is_set():
            return None

    elif task_type == "exam":
        on_progress(ProgressEvent("📝 命题组长正在疯狂敲键盘，为你量身定制试卷题目...", 0.4))
        blueprint = None
        if not diy_config:
            blueprint = build_blueprint(difficulty, (user_context or {}).get("target_score", 80), lang)
        markdown = generate_exam_paper(text, train_type, num_sets, difficulty, diy_config,
                                       user_context, lang, blueprint=blueprint)
        if stop_event.is_set():
            return None
        report = validate_paper(markdown or "", blueprint)
        extra_metrics["paper"] = report.metrics
        warnings.extend(report.issues)
        if not report.ok:
            logger.warning("试卷校验未通过: {}", report.issues[:5])
        doc_name = "训练试卷"

    else:
        raise ValueError(f"未知的任务类型: {task_type}")

    if not markdown:
        raise RuntimeError("生成结果为空")

    on_progress(ProgressEvent("🎨 正在渲染排版，并为你检查公式与换行...", 0.8))

    time_str = time.strftime("%m%d_%H%M", time.localtime())
    output_path = str(default_output_dir() / f"{course['name']}_{doc_name}_{time_str}.html")

    export_to_html(markdown, output_file=output_path, course=info, persona="AI",
                   doc_type=doc_name, lang=lang)

    db = get_db_session()
    try:
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
        **extra_metrics,
    }
    dump_debug(task_type, markdown, metrics)

    on_progress(ProgressEvent("✅ 渲染成功，准备展示！", 1.0))
    time.sleep(0.5)

    return RunResult(output_path=output_path, doc_type=doc_name, markdown=markdown,
                     metrics=metrics, warnings=warnings)
