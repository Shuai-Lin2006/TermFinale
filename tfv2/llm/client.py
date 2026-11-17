"""v2 LLM 客户端：只负责“给定 prompt，返回 JSON”。"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Protocol

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from core import config
from core import token_budget


class LLMError(RuntimeError):
    pass




def describe_llm_error(exc: Exception) -> str:
    """Turn provider/network failures into a message a student can act on.

    Keep this free of secrets: provider errors can echo request metadata, so we
    only return a short classification plus a bounded detail string.
    """
    status = getattr(exc, "status_code", None)
    text = str(exc or "").lower()
    detail = str(exc or "").strip().replace("\n", " ")[:180]
    if isinstance(exc, AuthenticationError) or status == 401 or "invalid api key" in text or "incorrect api key" in text:
        return "API Key 无效或已过期。请到「设置 → 模型」重新填写 DeepSeek Key，并点「测试连接」。"
    if isinstance(exc, PermissionDeniedError) or status == 403:
        return "API Key 没有访问该模型的权限。请检查 Key 所属账号和模型权限。"
    if status == 402 or any(word in text for word in ("insufficient balance", "insufficient_quota", "arrears", "billing", "balance is not enough", "quota exceeded")):
        return "API 账户余额不足或额度已用完。请充值，或在「设置 → 模型」更换可用的 Key。"
    if isinstance(exc, RateLimitError) or status == 429:
        return "API 请求过于频繁或已达限额。请稍等几分钟再试。"
    if isinstance(exc, APITimeoutError):
        return "连接模型服务超时。请检查网络或代理后重试。"
    if isinstance(exc, APIConnectionError):
        return "无法连接模型服务。请检查网络、代理或 DNS 后重试。"
    if isinstance(exc, BadRequestError) or status == 400:
        return f"模型请求参数被拒绝：{detail or '请检查模型名称和输入长度'}"
    if status and status >= 500:
        return "模型服务暂时不可用。请稍后重试；如果持续出现，请更换模型或检查服务状态。"
    return f"模型服务调用失败（{status or '网络/未知错误'}）。请稍后重试。{(' ' + detail) if detail else ''}".strip()


class LLMClient(Protocol):
    def json(self, system: str, user: str, *, max_tokens: int = 4096,
             temperature: float = 0.35) -> dict:
        ...


_INVALID_ESCAPE_RE = re.compile(r'\\(?![\\"/bfnrt]|u[0-9a-fA-F]{4})')


def _repair_invalid_escapes(text: str) -> str:
    """逐字符修复模型误写的 JSON 反斜杠（LaTeX \\mu / \\underline / 末尾反斜杠）。"""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= n:
            out.append("\\\\")
            i += 1
            continue
        nxt = text[i + 1]
        if nxt in '\\"/bfnrt':
            out.append(text[i:i + 2])
            i += 2
        elif nxt == "u" and i + 5 < n and all(c in "0123456789abcdefABCDEF" for c in text[i + 2:i + 6]):
            out.append(text[i:i + 6])
            i += 6
        else:
            out.append("\\\\")
            i += 1
    return "".join(out)

def _loads_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 模型偶尔在 evidence/note 里直接写 LaTeX，产生 Invalid \escape；
        # 先修反斜杠，再放宽控制字符，避免整页审计因格式问题失败。
        return json.loads(_repair_invalid_escapes(text), strict=False)


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise LLMError("模型返回为空")
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        value = _loads_json(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("模型没有返回 JSON")
        try:
            value = _loads_json(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError(f"模型 JSON 解析失败：{exc}") from exc
    if not isinstance(value, dict):
        raise LLMError("模型 JSON 顶层不是对象")
    return value


RETRYABLE_TYPES = ("APIConnectionError", "APITimeoutError", "RateLimitError",
                   "InternalServerError", "APIStatusError", "ConnectError",
                   "ReadTimeout", "RemoteProtocolError")
MAX_ATTEMPTS = 3


def is_retryable(exc: Exception) -> bool:
    """网络抖动/限流/5xx 值得重试；401、400 这类配置错误重试只会更糟。"""
    if isinstance(exc, (AuthenticationError, BadRequestError, PermissionDeniedError)):
        return False
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and (status == 429 or status >= 500):
        return True
    if isinstance(status, int) and 400 <= status < 500:
        return False
    return type(exc).__name__ in RETRYABLE_TYPES


class DeepSeekClient:
    """DeepSeek OpenAI 兼容客户端；key 从本机 .env 读取。"""

    def __init__(self, model: str | None = None, effort: str | None = None) -> None:
        config.load_env()
        key = (config.get_key("DEEPSEEK_API_KEY", "") or "").strip()
        if not key or key == "sk-not-configured":
            raise LLMError("没有配置 DEEPSEEK_API_KEY")
        try:
            timeout_s = float(os.getenv("TERMFINALE_LLM_TIMEOUT", "120"))
        except Exception:
            timeout_s = 120.0
        self._client = OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=max(20.0, timeout_s))
        self._model = model or config.text_model()
        self._effort = effort

    def _extra(self) -> dict:
        if self._effort:
            return {"reasoning_effort": self._effort}
        return config.model_extra(self._model)

    def json(self, system: str, user: str, *, max_tokens: int = 4096,
             temperature: float = 0.35) -> dict:
        try:
            token_budget.check()
        except RuntimeError as exc:
            raise LLMError(str(exc)) from exc
        args = dict(
            model=self._model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=min(max_tokens, config.max_tokens()),
            timeout=180,
            response_format={"type": "json_object"},
            **self._extra(),
        )
        last_exc: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = self._client.chat.completions.create(**args)
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= MAX_ATTEMPTS or not is_retryable(exc):
                    raise LLMError(describe_llm_error(exc)) from exc
                time.sleep(0.8 * attempt)   # 短暂退避：抖动多半几百毫秒就恢复
        else:  # pragma: no cover — 循环一定 break 或 raise
            raise LLMError(describe_llm_error(last_exc)) from last_exc
        content = resp.choices[0].message.content if resp.choices else ""
        try:
            from tfv2.llm import usage
            u = getattr(resp, "usage", None)
            usage.add(self._model,
                      prompt_tokens=int(getattr(u, "prompt_tokens", 0) or 0),
                      completion_tokens=int(getattr(u, "completion_tokens", 0) or 0),
                      total_tokens=int(getattr(u, "total_tokens", 0) or 0))
            token_budget.add(int(getattr(u, "total_tokens", 0) or 0))
        except Exception:
            pass
        return _parse_json(content or "")

    def chat(self, system: str, user: str, *, max_tokens: int = 2048,
             temperature: float = 0.3) -> str:
        try:
            token_budget.check()
        except RuntimeError as exc:
            raise LLMError(str(exc)) from exc
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=temperature,
                max_tokens=min(max_tokens, config.max_tokens()),
                timeout=120,
                **self._extra(),
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(describe_llm_error(exc)) from exc
        try:
            token_budget.add(int(getattr(resp.usage, "total_tokens", 0) or 0))
        except Exception:
            pass
        return (resp.choices[0].message.content if resp.choices else "") or ""

    def stream_messages(self, system: str, messages: list[dict], *, max_tokens: int = 2048,
                        temperature: float = 0.3):
        """逐 token 流式返回；预算在结束后按 usage 记账。"""
        payload = [{"role": "system", "content": system}]
        for m in messages:
            role = m.get("role")
            content = (m.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                payload.append({"role": role, "content": content})
        try:
            token_budget.check()
        except RuntimeError as exc:
            raise LLMError(str(exc)) from exc
        usage = 0
        text_chars = 0
        try:
            try:
                stream = self._client.chat.completions.create(
                    model=self._model, messages=payload, temperature=temperature,
                    max_tokens=min(max_tokens, config.max_tokens()), timeout=120,
                    stream=True, stream_options={"include_usage": True}, **self._extra(),
                )
                for chunk in stream:
                    try:
                        if getattr(chunk, "usage", None):
                            usage = int(chunk.usage.total_tokens or 0)
                    except Exception:
                        pass
                    if not getattr(chunk, "choices", None):
                        continue
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        text_chars += len(delta)
                        yield delta
            except Exception as exc:  # noqa: BLE001
                raise LLMError(describe_llm_error(exc)) from exc
        finally:
            try:
                # 部分兼容端点不返回 stream usage，用字符数保守估算。
                estimated = (len(system) + sum(len(str(m.get("content") or "")) for m in messages) + text_chars) // 4
                token_budget.add(max(usage, estimated))
            except Exception:
                pass


    def chat_messages(self, system: str, messages: list[dict], *, max_tokens: int = 2048,
                      temperature: float = 0.3) -> str:
        payload = [{"role": "system", "content": system}]
        for m in messages:
            role = m.get("role")
            content = (m.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                payload.append({"role": role, "content": content})
        try:
            token_budget.check()
        except RuntimeError as exc:
            raise LLMError(str(exc)) from exc
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=payload,
                temperature=temperature,
                max_tokens=min(max_tokens, config.max_tokens()),
                timeout=120,
                **self._extra(),
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(describe_llm_error(exc)) from exc
        try:
            token_budget.add(int(getattr(resp.usage, "total_tokens", 0) or 0))
        except Exception:
            pass
        return (resp.choices[0].message.content if resp.choices else "") or ""
