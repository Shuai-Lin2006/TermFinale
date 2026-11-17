"""Qwen-Image 装饰插图：只用于概念/氛围图，不用于精确题图。"""
from __future__ import annotations

import hashlib
import json
import ssl
import urllib.request
from pathlib import Path

from core.config import get_key, load_env

IMAGE_MODEL = "qwen-image-3.0"
IMAGE_REGION = "cn-beijing"
IMAGE_PRICE_USD = 0.024754
CACHE = Path(__file__).resolve().parents[2] / "data" / "ai_images"


class ImageGenError(RuntimeError):
    pass


def _endpoint() -> str:
    region = _env("TERMFINALE_IMAGE_REGION", IMAGE_REGION)
    return f"https://{region}.maas.qwencloudapi.com/compatible-mode/v1/images/generations"


def _env(name: str, default: str) -> str:
    import os
    return os.getenv(name, default).strip() or default


def generate(prompt: str, *, size: str = "1024x768", model: str | None = None) -> dict:
    load_env()
    key = get_key("DASHSCOPE_API_KEY", "")
    if not key or key == "sk-not-configured":
        raise ImageGenError("没有配置 DASHSCOPE_API_KEY")
    model = model or _env("TERMFINALE_IMAGE_MODEL", IMAGE_MODEL)
    digest = hashlib.sha256((model + size + prompt).encode("utf-8")).hexdigest()[:24]
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{digest}.png"
    if out.is_file():
        return {"path": str(out), "cached": True, "model": model, "price_usd": IMAGE_PRICE_USD}
    body = json.dumps({
        "model": model, "prompt": prompt, "n": 1, "size": size,
        "prompt_extend": False, "watermark": False,
        "negative_prompt": "text, letters, words, numbers, typography, labels, captions, documents, screenshots, UI, charts, tables, watermarks",
    }).encode()
    req = urllib.request.Request(
        _endpoint(), data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=600, context=ssl._create_unverified_context()) as r:
            data = json.loads(r.read().decode())
        url = (data.get("data") or [{}])[0].get("url")
        if not url:
            raise ImageGenError("图像接口没有返回 URL")
        with urllib.request.urlopen(url, timeout=180, context=ssl._create_unverified_context()) as r:
            out.write_bytes(r.read())
    except ImageGenError:
        raise
    except Exception as exc:
        raise ImageGenError(f"Qwen-Image 生成失败：{exc}") from exc
    return {"path": str(out), "cached": False, "model": model, "price_usd": IMAGE_PRICE_USD}
