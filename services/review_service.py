"""复习模式服务：逻辑分析 / 资料提取 / 训练试卷。

与旧实现保持同一套 prompt 与切块策略，只把 UI 依赖换成进度回调。
"""
from __future__ import annotations

import re
import threading
import time

from loguru import logger

from core.database import GeneratedFile as DBGeneratedFile, get_db_session
from core.exam_engine import generate_exam_paper, generate_extraction, generate_logic_analysis
from core.exporter import export_to_html
from services.task import (
    ProgressCb,
    ProgressEvent,
    RunResult,
    default_output_dir,
    dump_debug,
    noop_progress,
)
from services.guide_service import build_course_info

EXTRACT_CHUNK = 2000


def _run_extract(text: str, extract_type: str | None, with_answer: bool,
                 on_progress: ProgressCb, stop_event: threading.Event, started: float) -> str:
    chunks = [text[i:i + EXTRACT_CHUNK] for i in range(0, len(text), EXTRACT_CHUNK)]
    results: list[str] = []
    for i, chunk in enumerate(chunks):
        if stop_event.is_set():
            return ""
        eta = int((time.time() - started) / i * (len(chunks) - i)) if i > 0 else None
        on_progress(ProgressEvent(
            f"🔍 正在提取区块 {i + 1}/{len(chunks)}...", (i + 1) / len(chunks), eta))
        markdown = generate_extraction(chunk, extract_type, with_answer)
        if markdown:
            markdown = re.sub(r"以下是.*?考题。", "", markdown)
            markdown = re.sub(r"以下是.*?提取.*?：", "", markdown)
            results.append(markdown)
    return "\n\n".join(results)


def run_review(
    course: dict,
    task_type: str,
    text: str,
    *,
    extract_type: str | None = None,
    with_answer: bool = True,
    mode: str = "mindmap",
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

    if task_type == "extract":
        markdown = _run_extract(text, extract_type, with_answer, on_progress, stop_event, started)
        if stop_event.is_set():
            return None
        doc_name = "资料提取"

    elif task_type == "analysis":
        on_progress(ProgressEvent("🧠 AI 正在扫描文本，构建思维拓扑图...", 0.4))
        markdown = generate_logic_analysis(text, mode)
        if stop_event.is_set():
            return None
        doc_name = "逻辑分析" if mode == "text_logic" else "思维导图"

    elif task_type == "exam":
        on_progress(ProgressEvent("📝 命题组长正在疯狂敲键盘，为你量身定制试卷题目...", 0.4))
        markdown = generate_exam_paper(text, train_type, num_sets, difficulty, diy_config,
                                       user_context, lang)
        if stop_event.is_set():
            return None
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
    }
    dump_debug(task_type, markdown, metrics)

    on_progress(ProgressEvent("✅ 渲染成功，准备展示！", 1.0))
    time.sleep(0.5)

    return RunResult(output_path=output_path, doc_type=doc_name, markdown=markdown, metrics=metrics)
