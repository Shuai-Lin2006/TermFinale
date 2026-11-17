"""Optional Kimi/Moonshot client. Disabled unless KIMI_API_KEY is set."""
from __future__ import annotations

from openai import OpenAI

from core import config
from .client import LLMError, _parse_json


class KimiClient:
    """OpenAI-compatible Kimi client; no retries, capped output."""
    def __init__(self, model: str | None = None) -> None:
        config.load_env()
        key = (config.get_key("KIMI_API_KEY", "") or "").strip()
        if not key or key == "sk-not-configured":
            raise LLMError("没有配置 KIMI_API_KEY")
        self.model = model or config.get_key("KIMI_MODEL", "moonshot-v1-8k")
        self.base_url = config.get_key("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
        try:
            self.max_tokens = max(256, min(8192, int(config.get_key("KIMI_MAX_TOKENS", "4096"))))
        except ValueError:
            self.max_tokens = 4096
        self.client = OpenAI(api_key=key, base_url=self.base_url, timeout=90)

    def json(self, system: str, user: str, *, max_tokens: int = 4096,
             temperature: float = 0.2) -> dict:
        # K3 family only accepts temperature=1.
        if str(self.model).lower().startswith("kimi-k3"):
            temperature = 1
        try:
            res = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=temperature,
                max_tokens=min(int(max_tokens), self.max_tokens),
            )
            text = (res.choices[0].message.content or "").strip()
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Kimi 调用失败：{exc}") from exc
        if not text:
            raise LLMError("Kimi 返回为空")
        fence = chr(96) * 3
        text = text.replace(fence + "json", "").replace(fence, "").strip()
        return _parse_json(text)
