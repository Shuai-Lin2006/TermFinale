"""配置与密钥加载。

打包成 .app/.exe 后没有源码目录里的 `.env`，所以密钥必须支持
「用户数据目录」，否则粉丝双击启动就会因为 OpenAI 客户端拿不到 key 而崩。
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from core import paths

REQUIRED_KEYS = ("DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY")
PLACEHOLDER = "sk-not-configured"

_loaded = False


def env_candidates() -> list[Path]:
    """优先用户数据目录（可写、可分发），其次源码目录（开发期）。"""
    return [paths.data_dir() / ".env", paths.project_root() / ".env"]


def load_env(force: bool = False) -> list[Path]:
    global _loaded
    loaded: list[Path] = []
    if _loaded and not force:
        return loaded
    for candidate in env_candidates():
        try:
            if candidate.is_file():
                load_dotenv(candidate, override=False)
                loaded.append(candidate)
        except Exception as exc:  # 缺文件/权限问题都不该阻断启动
            logger.warning("读取环境文件失败 {}: {}", candidate, exc)
    _loaded = True
    return loaded


def get_key(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def missing_keys() -> list[str]:
    return [key for key in REQUIRED_KEYS if not get_key(key)]


def key_status() -> dict:
    return {key: bool(get_key(key)) for key in REQUIRED_KEYS}


def user_env_path() -> Path:
    """给设置页/文档用：用户应该把 .env 放在这里。"""
    return paths.data_dir() / ".env"


def save_key(name: str, value: str) -> Path:
    """把单个 key 写进用户目录的 .env（简单实现，后续可换 keyring）。"""
    paths.ensure_dirs()
    target = user_env_path()
    lines: list[str] = []
    if target.is_file():
        lines = [ln for ln in target.read_text(encoding="utf-8").splitlines()
                 if not ln.strip().startswith(f"{name}=")]
    lines.append(f"{name}={value.strip()}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[name] = value.strip()
    return target


def text_model() -> str:
    """文本模型：默认 deepseek-flash（实测可用且快），可用 DEEPSEEK_MODEL 覆盖。"""
    return get_key("DEEPSEEK_MODEL", "deepseek-flash")


def vision_model() -> str:
    """视觉模型：默认 qwen3-vl-plus（qwen-vl-max 在本账号 404），可用 QWEN_VL_MODEL 覆盖。"""
    return get_key("QWEN_VL_MODEL", "qwen3-vl-plus")
