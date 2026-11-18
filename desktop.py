"""TermFinale 新桌面外壳：本地 FastAPI + 系统 WebView（macOS WKWebView / Windows WebView2）。"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import threading
import time
import urllib.request
import shutil
import subprocess
from pathlib import Path

if getattr(sys, "frozen", False):
    # Keep every writable file under the platform's user-data directory.
    if sys.platform == "darwin":
        _app_home = Path.home() / "Library" / "Application Support" / "TermFinale"
    elif os.name == "nt":
        _app_home = Path(os.environ.get("APPDATA", str(Path.home()))) / "TermFinale"
    else:
        _app_home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "TermFinale"
    _user_data = _app_home / "v3-data"
    _user_data.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TERMFINALE_HOME", str(_app_home))
    os.environ.setdefault("TFV2_DATA_ROOT", str(_user_data))
    os.environ.setdefault("TFV2_PRODUCT_DB", str(_user_data / "product.sqlite3"))
    # The packaged app gets the same-origin guard plus session protection.
    os.environ.setdefault("TERMFINALE_PRODUCT_AUTH", "1")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PORT = int(os.getenv("TERMFINALE_WEB_PORT", "8900"))
V2_PORT = int(os.getenv("TFV2_PORT", "8905"))
PRODUCT_PORT = int(os.getenv("TFV3_PORT", "8907"))


def _port_free(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _pick_port(default: int) -> int:
    """Use the configured port when free, otherwise allocate a loopback port."""
    if _port_free(default):
        return default
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])
    finally:
        probe.close()


def _serve() -> None:
    import uvicorn
    from server.app import app
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def _serve_v2() -> None:
    """v2 讲义库/阅读器跑在同一个桌面进程里，旧 App 只负责入口。"""
    import uvicorn
    from tfv2.api.reader_app import app as v2app
    uvicorn.run(v2app, host="127.0.0.1", port=V2_PORT, log_level="warning")


def _serve_product() -> None:
    """v3 学习台：桌面默认入口，读 v2 artifact + 本地学习数据。"""
    try:
        import traceback
        import uvicorn
        from tfv2.api.product_app import app as product_app
        uvicorn.run(product_app, host="127.0.0.1", port=PRODUCT_PORT, log_level="warning")
    except BaseException:
        try:
            from core import paths
            paths.ensure_dirs()
            log = paths.logs_dir() / "server_error.log"
            log.write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        raise


def _port_up(port: int) -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=0.4)
        return True
    except Exception:  # noqa: BLE001
        return False


def _wait_server(timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PRODUCT_PORT}/api/health", timeout=0.6)
            return True
        except Exception:  # noqa: BLE001
            time.sleep(0.15)
    return False



class SplashScreen:
    """Borderless black splash; animation is driven only by Tk ``after`` callbacks."""

    WIDTH = 760
    HEIGHT = 430

    def __init__(self) -> None:
        import tkinter as tk

        self._tk = tk
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg="#000000")
        self.root.attributes("-alpha", 0.0)
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - self.WIDTH) // 2
        y = (sh - self.HEIGHT) // 2
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

        # Two dark, slightly larger labels sit behind the wordmark as a text glow.
        self.glow_outer = tk.Label(
            self.root, text="TermFinale", bg="#000000", fg="#101010",
            font=("PingFang SC", 82, "bold"),
        )
        self.glow_inner = tk.Label(
            self.root, text="TermFinale", bg="#000000", fg="#1c1c1c",
            font=("PingFang SC", 78, "bold"),
        )
        self.glow_outer.place(relx=0.5, rely=0.43, anchor="center", x=2, y=3)
        self.glow_inner.place(relx=0.5, rely=0.43, anchor="center", x=-1, y=-1)
        self.title = tk.Label(
            self.root, text="TermFinale", bg="#000000", fg="#ffffff",
            font=("PingFang SC", 74, "bold"),
        )
        self.title.place(relx=0.5, rely=0.43, anchor="center")
        self.tagline = tk.Label(
            self.root, text="高效 · efficiency", bg="#000000", fg="#86868B",
            font=("PingFang SC", 12),
        )
        self.tagline.place(relx=0.5, rely=0.62, anchor="center")

        self.root.bind("<Escape>", lambda _event: self.root.destroy())
        self.root.after(0, self._fade_in)

    def _fade_in(self, step: int = 0, steps: int = 15, interval: int = 20) -> None:
        alpha = min(1.0, (step + 1) / steps)
        try:
            self.root.attributes("-alpha", alpha)
        except Exception:
            pass
        if step + 1 < steps:
            self.root.after(interval, lambda: self._fade_in(step + 1, steps, interval))
        else:
            self.root.after(1000, self._fade_out)

    def _fade_out(self, step: int = 0, steps: int = 20, interval: int = 20) -> None:
        alpha = max(0.0, 1.0 - (step + 1) / steps)
        try:
            self.root.attributes("-alpha", alpha)
        except Exception:
            pass
        if step + 1 < steps:
            self.root.after(interval, lambda: self._fade_out(step + 1, steps, interval))
        else:
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def show_splash() -> None:
    try:
        SplashScreen().run()
    except Exception:
        # Splash must never prevent the application from opening.
        try:
            with open(Path(tempfile.gettempdir()) / "termfinale_splash.log", "a", encoding="utf-8") as f:
                import traceback
                f.write(traceback.format_exc())
        except Exception:
            pass

SPLASH_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><style>
  *{box-sizing:border-box}
  html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#0f1a13}
  body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
  .splash{position:relative;width:100%;height:100%;display:flex;align-items:center;justify-content:center;
    background:
      radial-gradient(ellipse 60% 70% at 50% 42%,rgba(216,255,66,.075),transparent 65%),
      radial-gradient(ellipse 80% 100% at 50% 110%,rgba(36,72,48,.65),transparent 70%),
      #0f1a13;
    opacity:0}
  .splash.run{animation:fadein .3s cubic-bezier(.22,.61,.36,1) forwards,fadeout .4s cubic-bezier(.4,0,1,1) 1.3s forwards}
  .splash:before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.18;
    background-image:radial-gradient(rgba(247,243,232,.16) .6px,transparent .6px);
    background-size:5px 5px;mask-image:radial-gradient(ellipse at center,black,transparent 78%)}
  .content{position:relative;text-align:center;transform:translateY(1px)}
  .eyebrow{font-size:9px;line-height:1;letter-spacing:.36em;text-transform:uppercase;color:#8e9c8b;
    margin-bottom:22px;opacity:0;animation:tagin .5s ease-out .16s forwards}
  .word{position:relative;display:inline-block;font-family:"Songti SC","STSong","New York",Georgia,serif;
    font-size:72px;font-weight:700;letter-spacing:-.055em;line-height:1;color:#f6f1e4;
    text-shadow:0 0 38px rgba(216,255,66,.10);
    opacity:0;filter:blur(7px);transform:translateY(14px) scale(.985);
    animation:wordin .62s cubic-bezier(.16,1,.3,1) .08s forwards}
  .rule{width:38px;height:1px;background:#d8ff42;margin:24px auto 15px;opacity:0;
    animation:tagin .45s ease-out .34s forwards}
  .tagline{font-size:10.5px;font-weight:300;letter-spacing:.27em;color:#aab4a5;line-height:1.5;
    opacity:0;animation:tagin .5s ease-out .4s forwards}
  .tagline b{font-weight:400;color:#d7ddcf}
  .meta{position:absolute;left:0;right:0;bottom:26px;text-align:center;font-size:8px;
    letter-spacing:.3em;color:#657366;text-transform:uppercase;opacity:0;animation:tagin .5s ease-out .5s forwards}
  @keyframes fadein{to{opacity:1}}
  @keyframes fadeout{to{opacity:0}}
  @keyframes wordin{to{opacity:1;filter:blur(0);transform:translateY(0) scale(1)}}
  @keyframes tagin{to{opacity:1}}
</style></head><body>
<div class="splash">
  <div class="content">
    <div class="eyebrow">Study desk</div>
    <div class="word">TermFinale</div>
    <div class="rule"></div>
    <div class="tagline"><b>高效</b> · efficiency</div>
  </div>
  <div class="meta">TermFinale · 学习工作台</div>
</div>
<script>
  (function(){
    var fired=false, started=false;
    function finish(){
      if(fired) return; fired=true;
      try { if(window.pywebview && window.pywebview.api) window.pywebview.api.done(); } catch(e) {}
    }
    function start(){
      if(started) return; started=true;
      var el=document.querySelector('.splash');
      if(el) el.classList.add('run');
      setTimeout(finish, 1720);
    }
    if(window.pywebview) start();
    else window.addEventListener('pywebviewready', start);
    // If the bridge injects late, starting anyway is safer than a stuck splash.
    setTimeout(start, 120);
  })();
</script>
</body></html>"""


class SplashBridge:
    """Callbacks used by the frameless splash WebView."""

    def __init__(self) -> None:
        self.splash = None
        self.main = None

    def done(self) -> bool:
        try:
            if self.splash is not None:
                self.splash.destroy()
        except Exception:
            pass
        try:
            if self.main is not None:
                self.main.show()
                self.main.restore()
        except Exception:
            pass
        return True




def _ensure_stdio() -> None:
    """窗口模式（console=False）下 sys.stdout/stderr 可能是 None，uvicorn/logging 会崩。"""
    import os
    import sys
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

def _find_edge() -> str | None:
    if sys.platform == "win32":
        roots = [
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("ProgramFiles"),
            os.environ.get("LOCALAPPDATA"),
            r"C:\Program Files (x86)",
            r"C:\Program Files",
        ]
        candidates = []
        for root in roots:
            if root:
                candidates.append(str(Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"))
        candidates += [shutil.which("msedge"), shutil.which("msedge.exe")]
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe")
            candidates.append(winreg.QueryValue(key, None))
            winreg.CloseKey(key)
        except Exception:
            pass
    elif sys.platform == "darwin":
        candidates = ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    else:
        candidates = [shutil.which("microsoft-edge"), shutil.which("google-chrome")]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def _open_edge_app(url: str, wait: bool = True) -> int:
    """WebView 不可用时的兜底：用系统 Edge 的 app 模式打开同一个本地页面。"""
    edge = _find_edge()
    if not edge:
        print("未找到 Microsoft Edge，无法打开界面")
        return 1
    profile = os.path.join(tempfile.gettempdir(), "termfinale-edge-profile")
    args = [edge, f"--app={url}", "--window-size=1440,920",
            f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check"]
    try:
        with open(Path(tempfile.gettempdir()) / "termfinale_boot.log", "a", encoding="utf-8") as f:
            f.write(f"edge fallback url={url} edge={edge}\n")
    except Exception:
        pass
    proc = subprocess.Popen(args)
    if wait:
        proc.wait()
    return 0

def main() -> int:
    _ensure_stdio()
    from core import config, paths

    config.load_env()
    paths.ensure_dirs()

    try:
        from core.local_bridge import start_bridge
        start_bridge()
    except Exception:  # noqa: BLE001
        pass

    global PORT, V2_PORT, PRODUCT_PORT
    PORT = _pick_port(PORT)
    V2_PORT = _pick_port(V2_PORT)
    PRODUCT_PORT = _pick_port(PRODUCT_PORT)
    # Keep the legacy auth/CORS code and any child import on the same ports
    # that the WebView actually uses.
    os.environ["TERMFINALE_WEB_PORT"] = str(PORT)
    os.environ["TFV2_PORT"] = str(V2_PORT)
    os.environ["TFV3_PORT"] = str(PRODUCT_PORT)
    # v3 is the only UI the desktop shell opens. The legacy 8900/8905
    # services stay available for source/legacy use, but are not started in
    # the packaged app: fewer ports, no duplicate DB writers, no stale routes.
    threading.Thread(target=_serve_product, daemon=True).start()

    if not _wait_server():
        print("本地服务启动失败")
        return 1

    if os.getenv("TERMFINALE_UI", "").strip().lower() == "edge":
        return _open_edge_app(f"http://127.0.0.1:{PRODUCT_PORT}/")


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
                    with open(Path(tempfile.gettempdir()) / "tf_swipe.log", "a", encoding="utf-8") as f:
                        f.write(f"BrowserView patched, gestures={self.webview.allowsBackForwardNavigationGestures()}\n")
                except Exception as e:
                    with open(Path(tempfile.gettempdir()) / "tf_swipe.log", "a", encoding="utf-8") as f:
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
            with open(Path(tempfile.gettempdir()) / "tf_swipe.log", "a", encoding="utf-8") as f:
                f.write("swipe monitor installed\n")
        except Exception as e:
            with open(Path(tempfile.gettempdir()) / "tf_swipe.log", "a", encoding="utf-8") as f:
                f.write(f"swipe monitor failed: {e}\n")

    import webview

    splash_bridge = SplashBridge()
    try:
        from core.build_info import VERSION as _VERSION
    except Exception:
        _VERSION = "0.4.7"
    main_window = webview.create_window(
        f"TermFinale {_VERSION}",
        f"http://127.0.0.1:{PRODUCT_PORT}/",
        width=1440, height=920, min_size=(1080, 700),
        background_color="#FAFAF8",
        hidden=True,
    )
    splash_window = webview.create_window(
        "TermFinale",
        html=SPLASH_HTML,
        width=760, height=430,
        frameless=True, on_top=True, resizable=False, easy_drag=False,
        background_color="#0f1a13",
        js_api=splash_bridge,
        hidden=True,
    )
    splash_bridge.splash = splash_window
    splash_bridge.main = main_window

    def _quit_on_close() -> None:
        try:
            os._exit(0)
        except Exception:
            pass
    try:
        main_window.events.closed += _quit_on_close
    except Exception:
        pass
    window = main_window

    def _show_splash():
        try:
            splash_window.show()
            splash_window.evaluate_js("document.querySelector('.splash').classList.add('run')")
        except Exception:
            pass
        # Safety net: never leave the main window hidden if the JS bridge fails.
        try:
            threading.Timer(2.6, splash_bridge.done).start()
        except Exception:
            pass

    splash_window.events.loaded += _show_splash

    def _disable_swipe_back():
        """macOS：关闭 WKWebView 横向滑动返回，避免输入框拖选误触。"""
        if sys.platform != "darwin":
            return
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
            with open(Path(tempfile.gettempdir()) / "termfinale_swipe.log", "a", encoding="utf-8") as f:
                f.write(f"native={type(native).__name__} webview={type(webview_obj).__name__} "
                        f"has_setter={hasattr(webview_obj, 'setAllowsBackForwardNavigationGestures_')}\n")
        except Exception as e:
            with open(Path(tempfile.gettempdir()) / "termfinale_swipe.log", "a", encoding="utf-8") as f:
                f.write(f"ERROR {e}\n")

    webview.start(_disable_swipe_back)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
