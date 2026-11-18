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




def _ensure_stdio() -> None:
    """窗口模式（console=False）下 sys.stdout/stderr 可能是 None，uvicorn/logging 会崩。"""
    import os
    import sys
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

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
    _ensure_stdio()
    try:
        from core.single_instance import acquire

        if not acquire():
            # 已有实例：尝试直接打开它的界面，而不是只弹“正在运行”
            try:
                import urllib.request
                for port in (8907, 8905, 8900, 8906, 8910):
                    try:
                        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=0.5)
                    except Exception:
                        continue
                    from desktop import _open_edge_app
                    _open_edge_app(f"http://127.0.0.1:{port}/", wait=False)
                    return
            except Exception:
                pass
            # 锁被占但没有可用服务：不再把用户挡在门外，继续启动（多实例风险由端口隔离兜底）
            write_crash("检测到旧实例锁，但服务不可用；继续启动新实例。")
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
                raise RuntimeError("Edge 窗口也启动失败，见 termfinale_boot.log / logs")

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
