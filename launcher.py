"""打包入口：先装崩溃日志，再启动应用。

窗口模式（console=False）下，导入期异常不会显示在任何地方，
所以必须在这里兜底写文件，否则用户只看到"双击没反应"。
"""
from __future__ import annotations

import datetime
import os
import sys
import traceback
from pathlib import Path

# Bundled Typst produces an additional publication PDF. It is a secondary
# artifact and cannot break the normal HTML/KaTeX PDF (build catches errors).
os.environ.setdefault("TERMFINALE_TYPST", "1")


def _candidate_log_dirs() -> list[Path]:
    dirs: list[Path] = []
    try:
        from core import paths  # 正常路径：与运行期一致的日志目录

        dirs.append(paths.logs_dir())
    except Exception:
        pass
    home = Path.home()
    if sys.platform == "darwin":
        dirs.append(home / "Library" / "Application Support" / "TermFinale" / "logs")
    elif os.name == "nt":
        dirs.append(Path(os.environ.get("APPDATA", str(home))) / "TermFinale" / "logs")
    else:
        dirs.append(home / ".local" / "share" / "TermFinale" / "logs")
    return dirs


def write_crash(text: str) -> str | None:
    for directory in _candidate_log_dirs():
        try:
            directory.mkdir(parents=True, exist_ok=True)
            with (directory / "crash.log").open("a", encoding="utf-8") as fh:
                fh.write(text)
            return str(directory)
        except Exception:
            continue
    return None


def _notify(text: str, where: str | None) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("TermFinale 启动失败",
                             f"{text[:1200]}\n\n日志目录：{where or '（写入失败）'}")
        root.destroy()
    except Exception:
        pass


def main() -> None:
    try:
        from core.single_instance import acquire

        if not acquire():
            _notify("TermFinale 已经在运行，请先退出旧窗口再重新打开。", None)
            return
    except Exception:
        pass
    try:
        if os.getenv("TERMFINALE_UI", "web").strip().lower() != "tk":
            try:
                from desktop import main as web_main

                result = web_main()
                if result == 0:
                    return
                raise RuntimeError(f"WebView 外壳返回 {result}")
            except Exception:
                write_crash("WebView 外壳启动失败，改用 Edge 窗口\n" + traceback.format_exc())
                os.environ["TERMFINALE_UI"] = "edge"
                from desktop import main as edge_main

                if edge_main() == 0:
                    return

        import main as app_main

        app_main.run()
    except BaseException:
        detail = f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] 启动失败\n" + traceback.format_exc()
        where = write_crash(detail)
        _notify(detail, where)
        raise


if __name__ == "__main__":
    # Required for frozen Windows builds that spawn worker processes.
    import multiprocessing
    multiprocessing.freeze_support()
    main()
