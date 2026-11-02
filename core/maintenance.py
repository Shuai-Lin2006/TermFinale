"""本地数据维护：缓存统计与调试产物清理。

原则：只清理**可再生**的产物（debug/ 下的原始输出），不碰用户资料、
不碰生成好的 HTML。删除前先报告，调用方决定是否执行。
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger

from core import paths


def human_size(num: int) -> str:
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}B"
        size /= 1024
    return f"{size:.1f}GB"


def dir_stats(path: Path) -> dict:
    files = 0
    total = 0
    if path.exists():
        for item in path.rglob("*"):
            if item.is_file():
                files += 1
                try:
                    total += item.stat().st_size
                except OSError:
                    pass
    return {"path": str(path), "files": files, "bytes": total, "human": human_size(total)}


def cache_report() -> dict:
    """各目录占用情况，供设置页展示。"""
    return {
        "assets": dir_stats(paths.assets_dir()),
        "debug": dir_stats(paths.debug_dir()),
        "logs": dir_stats(paths.logs_dir()),
        "outputs": dir_stats(paths.outputs_dir()),
    }


def prune_debug(keep: int = 100) -> dict:
    """只保留最近 keep 个调试文件（按修改时间），删除更早的。

    这些是 AI 原始输出与指标，可随时由重新生成得到，不含用户原始资料。
    """
    path = paths.debug_dir()
    if not path.exists():
        return {"removed": 0, "freed": 0, "kept": 0}
    files = sorted((p for p in path.iterdir() if p.is_file()),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    freed = 0
    for stale in files[keep:]:
        try:
            freed += stale.stat().st_size
            stale.unlink()
            removed += 1
        except OSError as exc:
            logger.warning("删除调试文件失败 {}: {}", stale.name, exc)
    if removed:
        logger.info("清理调试产物 {} 个，释放 {}", removed, human_size(freed))
    return {"removed": removed, "freed": freed, "kept": min(keep, len(files))}
