"""统一日志：文件落盘（UTF-8）+ 轮转 + 全局/线程/Tk 回调异常钩子。

Windows 上控制台是 GBK，日志文件必须显式 UTF-8，否则中文会乱码或抛错。
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from loguru import logger

from core import paths

_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <7}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {name}:{function}:{line} - {message}"

_CONFIGURED = False


def setup_logging(level: str = "INFO", console: bool = True) -> Path | None:
    """初始化日志。重复调用安全。返回日志目录（不可写时返回 None）。"""
    global _CONFIGURED
    if _CONFIGURED:
        return paths.logs_dir()

    logger.remove()
    if console:
        logger.add(
            sys.stderr,
            level=level,
            colorize=sys.stderr.isatty(),
            format=_FORMAT,
            backtrace=False,
            diagnose=False,
        )

    log_file = None
    try:
        paths.ensure_dirs()
        log_file = paths.logs_dir() / "app_{time:YYYY-MM-DD}.log"
        logger.add(
            str(log_file),
            level="DEBUG",
            format=_FILE_FORMAT,
            rotation="5 MB",
            retention=10,
            encoding="utf-8",
            enqueue=False,
            backtrace=True,
            diagnose=False,
        )
    except Exception as exc:  # 日志失败绝不能拖垮程序
        logger.warning(f"文件日志不可用：{exc}")

    _CONFIGURED = True
    logger.debug("日志初始化完成 dir={} file={}", paths.logs_dir(), log_file)
    return paths.logs_dir()


def _excepthook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.opt(exception=(exc_type, exc_value, exc_tb)).critical("未捕获异常")


def _thread_excepthook(args):
    logger.opt(exception=(args.exc_type, args.exc_value, args.exc_traceback)).critical(
        "线程未捕获异常 thread={}", args.thread.name if args.thread else "unknown"
    )


def install_exception_hooks(tk_root=None) -> None:
    """接管 sys / threading / Tk 三处异常，保证崩溃有迹可循。"""
    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook
    if tk_root is not None:
        def _tk_cb(exc, val, tb):
            logger.opt(exception=(exc, val, tb)).error("Tk 回调异常")
            # 按钮点了没反应，往往就是这里被吞掉了；给用户一个可见提示
            try:
                from tkinter import messagebox

                messagebox.showerror("操作失败", f"{exc.__name__}: {val}"[:600])
            except Exception:
                pass

        try:
            tk_root.report_callback_exception = _tk_cb
        except Exception:
            pass
