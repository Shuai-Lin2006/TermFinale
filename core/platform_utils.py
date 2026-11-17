"""跨平台打开文件/网页。

旧实现写死 ``open -a "Microsoft Edge"``：macOS 专属，且 ``subprocess.run``
在 App 不存在时只返回非 0、不抛异常，导致 fallback 永远不触发。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from loguru import logger


def find_soffice() -> str | None:
    """Locate LibreOffice even when the packaged app has a minimal PATH."""
    env = os.getenv("TERMFINALE_SOFFICE", "").strip()
    candidates = [
        env,
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/opt/homebrew/bin/soffice",
        "/usr/local/bin/soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def to_uri(path: str | Path) -> str:
    return Path(path).expanduser().resolve().as_uri()


def open_path(path: str | Path) -> bool:
    """用系统默认程序打开。返回是否成功。"""
    target = Path(path).expanduser()
    if not target.exists():
        logger.warning("文件不存在，无法打开: {}", target)
        return False

    uri = to_uri(target)

    # macOS：装了 Edge 就优先用它（用户习惯），否则回退默认浏览器
    if sys.platform == "darwin" and Path("/Applications/Microsoft Edge.app").exists():
        proc = subprocess.run(["open", "-a", "Microsoft Edge", uri], capture_output=True, timeout=15)
        if proc.returncode == 0:
            return True

    # 首选：交给系统默认处理器（三端一致，html 会用默认浏览器）
    try:
        if webbrowser.open(uri):
            return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("webbrowser 打开失败: {}", exc)

    # 兜底：平台命令，返回值一定要检查
    try:
        if os.name == "nt":
            os.startfile(str(target))  # type: ignore[attr-defined]
            return True
        cmd = ["open", str(target)] if sys.platform == "darwin" else ["xdg-open", str(target)]
        proc = subprocess.run(cmd, capture_output=True, timeout=15)
        if proc.returncode == 0:
            return True
        logger.warning("系统打开失败 rc={} err={}", proc.returncode,
                       proc.stderr.decode(errors="ignore")[:200])
    except Exception as exc:  # noqa: BLE001
        logger.warning("打开文件异常: {}", exc)
    return False
