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


    # macOS：给 pywebview 的 BrowserView 打补丁，创建 WKWebView 后立即关闭滑动返回
    if sys.platform == "darwin":
        try:
            from webview.platforms import cocoa as _cocoa
            _orig_init = _cocoa.BrowserView.__init__

            def _patched_init(self, *args, **kwargs):
                _orig_init(self, *args, **kwargs)
                try:
                    self.webview.setAllowsBackForwardNavigationGestures_(False)
                    self.webview.setValue_forKey_(False, "allowsBackForwardNavigationGestures")
                    with open("/tmp/tf_swipe.log", "a") as f:
                        f.write(f"BrowserView patched, gestures={self.webview.allowsBackForwardNavigationGestures()}\n")
                except Exception as e:
                    with open("/tmp/tf_swipe.log", "a") as f:
                        f.write(f"BrowserView patch failed: {e}\n")

            _cocoa.BrowserView.__init__ = _patched_init
        except Exception:
            pass


    # macOS：吞掉系统 swipe 事件（WKWebView 滑动返回的源头）
    if sys.platform == "darwin":
        try:
            from AppKit import NSEvent
            NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
                1 << 31, lambda event: None)  # NSEventTypeSwipe
            with open("/tmp/tf_swipe.log", "a") as f:
                f.write("swipe monitor installed\n")
        except Exception as e:
            with open("/tmp/tf_swipe.log", "a") as f:
                f.write(f"swipe monitor failed: {e}\n")

    import webview

    window = webview.create_window(
        "TermFinale",
        f"http://127.0.0.1:{PORT}/dashboard.html",
        width=1440, height=920, min_size=(1080, 700),
        background_color="#FAFAF8",
    )

    def _disable_swipe_back():
        """macOS：关闭 WKWebView 横向滑动返回，避免输入框拖选误触。"""
        try:
            native = None
            for _ in range(150):
                native = getattr(window, "native", None)
                if native is not None:
                    break
                time.sleep(0.1)
            # 从 NSWindow 递归找真正的 WKWebView
            def _find_wk(obj, depth=0):
                if obj is None or depth > 6:
                    return None
                if hasattr(obj, "setAllowsBackForwardNavigationGestures_"):
                    return obj
                try:
                    children = []
                    if hasattr(obj, "contentView"):
                        children.append(obj.contentView())
                    if hasattr(obj, "subviews"):
                        children.extend(list(obj.subviews()))
                    for ch in children:
                        found = _find_wk(ch, depth + 1)
                        if found is not None:
                            return found
                except Exception:
                    pass
                return None
            webview_obj = _find_wk(native)
            if webview_obj is None:
                try:
                    from webview.platforms.cocoa import BrowserView
                    for _ in range(100):
                        if BrowserView.instances:
                            webview_obj = list(BrowserView.instances.values())[0].webview
                            break
                        time.sleep(0.1)
                except Exception:
                    pass
            if webview_obj is not None and hasattr(webview_obj, "setAllowsBackForwardNavigationGestures_"):
                webview_obj.setAllowsBackForwardNavigationGestures_(False)
            if webview_obj is not None:
                try:
                    webview_obj.setValue_forKey_(False, "allowsBackForwardNavigationGestures")
                except Exception:
                    pass
            with open("/tmp/termfinale_swipe.log", "a") as f:
                f.write(f"native={type(native).__name__} webview={type(webview_obj).__name__} "
                        f"has_setter={hasattr(webview_obj, 'setAllowsBackForwardNavigationGestures_')}\n")
        except Exception as e:
            with open("/tmp/termfinale_swipe.log", "a") as f:
                f.write(f"ERROR {e}\n")

    webview.start(_disable_swipe_back)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
