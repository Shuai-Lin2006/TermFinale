"""本地问答桥：让生成的 HTML 能「选中文字提问」，而 API Key 始终留在应用里。

安全模型：
- 只监听 127.0.0.1
- 每次启动生成随机令牌，写进用户数据目录的 bridge.json；HTML 只拿到这个令牌
- 每个请求校验 X-TF-Token，限制请求频率
"""
from __future__ import annotations

import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from loguru import logger
from openai import OpenAI

from core import paths
from core.config import get_key, load_env, max_tokens, model_extra, text_model

_BRIDGE_FILE = "bridge.json"
_state: dict = {"server": None, "port": None, "token": None}
_rate: list[float] = []
_RATE_LIMIT = 12  # 每分钟最多 12 次

_SYSTEM = """你是期末复习助教，像坐在学生旁边的老师一样回答。
规则：
1. 用户选中的【资料片段】就是依据。片段里有定义、公式、步骤时，必须直接解释，绝对不要要求用户重新贴原文，也不要说「资料未涉及」。
2. 只有当片段确实为空或只有章节标题时，才说「这段资料没有展开」，然后给出【延伸】解释。
3. 先给一句直接结论，再拆步骤或举一个例子；不要客套，不要复述问题。
4. 公式用 $...$ 包裹；不要编造页码、定理编号。
5. 回答控制在 500 字以内，但要把话说完整，不能只给一句敷衍。"""

_MODES = {
    "explain": "请用通俗的话解释这段内容，必要时给一个类比。",
    "example": "请给一个具体的、期末可能考的例子，并说明解题步骤。",
    "quiz": "请基于这段内容出一道小题（附答案），难度对标期末考试。",
}


def bridge_config() -> dict | None:
    """供 exporter 读取；未启动时返回 None。"""
    try:
        data = json.loads((paths.data_dir() / _BRIDGE_FILE).read_text(encoding="utf-8"))
        if data.get("port") and data.get("token"):
            return data
    except (OSError, ValueError):
        pass
    return None


def _answer(payload: dict) -> str:
    context = (payload.get("context") or "").strip()[:24000]
    question = (payload.get("question") or "").strip()[:500]
    mode = payload.get("mode") or "explain"
    course = (payload.get("course") or "").strip()[:80]
    chapter = (payload.get("chapter") or "").strip()[:120]
    if not question:
        return "没有收到问题。"

    load_env()
    prompt = (f"课程：{course or '未知'}\n章节：{chapter or '未知'}\n"
              f"【讲义内容 / 用户选中的片段】（这是你的依据；选中时优先针对选中部分）\n"
              f"{context or '（空）'}\n\n"
              f"【问题】{question}\n{_MODES.get(mode, _MODES['explain'])}\n"
              f"如果片段里有定义或公式，直接解释它；不要要求用户再贴一次。")
    client = OpenAI(api_key=get_key("DEEPSEEK_API_KEY", "sk-not-configured"),
                    base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=text_model(), max_tokens=min(1800, max_tokens()), temperature=0.3,
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": prompt}],
        **model_extra())
    return (resp.choices[0].message.content or "").strip() or "模型没有返回内容，请重试。"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 静音
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-TF-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/health"):
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/api/ask"):
            self._json(404, {"error": "not found"})
            return
        if self.headers.get("X-TF-Token") != _state["token"]:
            self._json(403, {"error": "forbidden"})
            return

        now = time.time()
        _rate[:] = [t for t in _rate if now - t < 60]
        if len(_rate) >= _RATE_LIMIT:
            self._json(429, {"error": "提问太频繁，稍等一下"})
            return
        _rate.append(now)

        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            self._json(200, {"answer": _answer(payload)})
        except Exception as exc:  # noqa: BLE001
            logger.error("问答失败: {}", exc)
            self._json(500, {"error": f"{type(exc).__name__}: {exc}"})


def start_bridge() -> bool:
    if _state["server"]:
        return True
    token = secrets.token_urlsafe(18)
    for port in range(8765, 8785):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
        except OSError:
            continue
        _state.update(server=server, port=port, token=token)
        try:
            paths.ensure_dirs()
            bridge_file = paths.data_dir() / _BRIDGE_FILE
            bridge_file.write_text(json.dumps({"port": port, "token": token}), encoding="utf-8")
            try:
                bridge_file.chmod(0o600)
            except OSError:
                pass
        except OSError:
            pass
        threading.Thread(target=server.serve_forever, daemon=True).start()
        logger.info("问答桥已启动: 127.0.0.1:{}", port)
        return True
    logger.warning("问答桥端口全部被占用，选中提问将不可用")
    return False


def stop_bridge() -> None:
    server = _state.get("server")
    if server:
        server.shutdown()
        server.server_close()
        _state["server"] = None
