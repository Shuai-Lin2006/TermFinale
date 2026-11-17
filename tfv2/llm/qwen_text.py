"""Qwen text client: second provider for pages DeepSeek refuses/empties."""
from __future__ import annotations

import json
import os

from openai import OpenAI

from core.config import get_key, load_env
from tfv2.llm.client import LLMError


class QwenTextClient:
    def __init__(self, model: str | None = None):
        load_env()
        self.model = model or os.getenv("TERMFINALE_QWEN_TEXT_MODEL", "qwen-plus")
        self.client = OpenAI(
            api_key=get_key("DASHSCOPE_API_KEY", "sk-not-configured"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    def json(self, system: str, user: str, *, max_tokens: int = 4096, temperature: float = 0.2) -> dict:
        max_tokens = max(1, min(int(max_tokens), 8192))
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=90,
            )
            text = (res.choices[0].message.content or "").strip()
            try:
                from tfv2.llm import usage
                u = getattr(res, "usage", None)
                usage.add(self.model,
                          prompt_tokens=int(getattr(u, "prompt_tokens", 0) or 0),
                          completion_tokens=int(getattr(u, "completion_tokens", 0) or 0),
                          total_tokens=int(getattr(u, "total_tokens", 0) or 0))
            except Exception:
                pass
        except Exception as exc:
            raise LLMError(f"Qwen 调用失败：{exc}") from exc
        if not text:
            raise LLMError("Qwen 返回为空")
        fence = chr(96) * 3
        text = text.replace(fence + "json", "").replace(fence, "").strip()
        try:
            data = json.loads(text)
        except Exception as exc:
            raise LLMError(f"Qwen JSON 解析失败：{exc}") from exc
        if not isinstance(data, dict):
            raise LLMError("Qwen 没有返回 JSON 对象")
        return data
