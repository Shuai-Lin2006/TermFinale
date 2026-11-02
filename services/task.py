"""服务层公共模型：进度事件、运行结果、调试产物落盘。"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from loguru import logger

from core import paths


@dataclass
class ProgressEvent:
    """一次进度上报。UI 决定怎么画，服务层只描述事实。"""

    message: str
    value: float = 0.0          # 0.0 ~ 1.0
    eta_seconds: int | None = None


@dataclass
class RunResult:
    """一次生成任务的产物。"""

    output_path: str
    doc_type: str
    markdown: str = ""
    metrics: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


ProgressCb = Callable[[ProgressEvent], None]


def noop_progress(_event: ProgressEvent) -> None:
    """默认回调：不关心进度时用。"""


def default_output_dir() -> Path:
    """生成物默认落桌面；可用 TERMFINALE_OUTPUT_DIR 覆盖（测试/自定义导出目录）。"""
    override = os.getenv("TERMFINALE_OUTPUT_DIR", "").strip()
    if override:
        path = Path(override).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path
    desktop = Path.home() / "Desktop"
    if desktop.is_dir():
        return desktop
    paths.ensure_dirs()
    return paths.outputs_dir()


def dump_debug(kind: str, markdown: str, meta: dict | None = None) -> Path | None:
    """把原始 Markdown 与指标落盘，供事后复盘（失败样本）。

    这是"内容不稳定"能被诊断的前提：以前只存了渲染后的 HTML，AI 原始输出无从追查。
    """
    try:
        paths.ensure_dirs()
        stamp = time.strftime("%Y%m%d_%H%M%S")
        md_path = paths.debug_dir() / f"{stamp}_{kind}.md"
        md_path.write_text(markdown or "", encoding="utf-8")
        meta_path = paths.debug_dir() / f"{stamp}_{kind}.json"
        meta_path.write_text(
            json.dumps(meta or {}, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        logger.debug("调试产物已落盘: {}", md_path.name)
        return md_path
    except OSError as exc:
        logger.warning("调试产物落盘失败: {}", exc)
        return None
