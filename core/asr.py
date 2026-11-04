"""音频转文字：调用 DashScope qwen3-asr-flash（支持本地 file:// 路径）。"""
from __future__ import annotations

import os
from pathlib import Path

from loguru import logger

from core.config import get_key, load_env

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".amr"}
MAX_MB = 100


def is_audio(path: str) -> bool:
    return Path(path).suffix.lower() in AUDIO_EXTS


def transcribe_audio(file_path: str, on_progress=None) -> str:
    load_env()
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"音频不存在：{path}")
    if path.stat().st_size > MAX_MB * 1024 * 1024:
        raise ValueError(f"音频超过 {MAX_MB}MB，请先压缩或分段")

    key = get_key("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("未配置阿里云百炼 Key，无法转写音频")

    if on_progress:
        on_progress(0, 1, "asr")

    import dashscope
    from dashscope import MultiModalConversation

    dashscope.api_key = key
    resp = MultiModalConversation.call(
        model=os.getenv("TERMFINALE_ASR_MODEL", "qwen3-asr-flash"),
        messages=[{"role": "user", "content": [{"audio": f"file://{path}"}]}],
    )
    if getattr(resp, "status_code", 0) != 200:
        raise RuntimeError(f"音频转写失败：{getattr(resp, 'code', '')} {getattr(resp, 'message', '')}")

    texts: list[str] = []
    try:
        for choice in resp.output["choices"]:
            for item in choice["message"]["content"]:
                if item.get("text"):
                    texts.append(item["text"])
    except Exception as exc:  # noqa: BLE001
        logger.error("解析音频结果失败: {}", exc)
        raise RuntimeError("音频转写结果为空") from exc

    text = "\n".join(texts).strip()
    if on_progress:
        on_progress(1, 1, "asr")
    if not text:
        raise RuntimeError("没有识别到语音内容")
    return text
