"""把内部异常翻译成用户能照做的中文提示。

为什么不在前端做：generate / exam / fuse 失败时后端已经把 error 存进任务记录，
前端只是照读；在这里翻译一次，所有入口（任务卡、toast、重试）都一致。
底线：保留原因，但不把 `RuntimeError:` 这种类名甩给用户；翻译不出来就截断原文。
"""
from __future__ import annotations

import re

from tfv2.llm.client import LLMError, describe_llm_error

_CLASS_PREFIX = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception|Timeout)(?::\s*|$)")

_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"DEEPSEEK_API_KEY|API Key|401|unauthorized", re.I),
     "模型 Key 还没配好：到「设置 → 模型」填写 DeepSeek Key，点「测试连接」后再试。"),
    (re.compile(r"超时|timeout|timed out", re.I),
     "模型响应超时：稍等重试一次；资料页多的话先少选几页。"),
    (re.compile(r"限流|429|rate limit", re.I),
     "请求太频繁被限流了：等十几秒再试，别连点。"),
    (re.compile(r"连接|connection|network|fetch", re.I),
     "网络没连上模型服务：检查网络后重试。"),
    (re.compile(r"缺 sections\.json|没有讲义结构|sections\.json"),
     "这份资料还没生成讲义结构，出卷前先点「生成讲义」。"),
    (re.compile(r"全部排除|被用户全部排除"),
     "你把这份资料的内容都排除了：恢复一部分再生成。"),
]


def friendly_reason(exc: Exception, *, limit: int = 200) -> str:
    """异常 → 一句原因 + 一句下一步；翻不出来时保留原文（截断）。"""
    raw = str(exc or "").strip()
    body = _CLASS_PREFIX.sub("", raw).strip() or raw
    for pattern, hint in _HINTS:
        if pattern.search(body):
            # 原因 + 下一步，原因放前面，便于用户核对
            tail = f"（{body}）" if body and body not in hint else ""
            text = hint + tail
            return text if len(text) <= limit else text[:limit] + "…"
    if isinstance(exc, LLMError):
        detail = describe_llm_error(exc)
        return detail if len(detail) <= limit else detail[:limit] + "…"
    if not body:
        return "这次没成功，但原因没写清楚；可以重试一次，或换个资料页再试。"
    text = body if len(body) <= limit else body[:limit] + "…"
    return f"{text}（可以重试一次；仍失败就换几页资料再试）"
