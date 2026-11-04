"""TermFinale 新桌面外壳：本地 FastAPI + 系统 WebView（macOS WKWebView / Windows WebView2）。"""
from __future__ import annotations

import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PORT = int(os.getenv("TERMFINALE_WEB_PORT", "8900"))


def _serve() -> None:
    import uvicorn
    from server.app import app
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def _wait_server(timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=0.6)
            return True
        except Exception:  # noqa: BLE001
            time.sleep(0.15)
    return False


def main() -> int:
    from core import config, paths

    config.load_env()
    paths.ensure_dirs()

    try:
        from core.local_bridge import start_bridge
        start_bridge()
    except Exception:  # noqa: BLE001
        pass

    threading.Thread(target=_serve, daemon=True).start()
    if not _wait_server():
        print("本地服务启动失败")
        return 1

    import webview

    webview.create_window(
        "TermFinale",
        f"http://127.0.0.1:{PORT}/dashboard.html",
        width=1440, height=920, min_size=(1080, 700),
        background_color="#FAFAF8",
    )
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
