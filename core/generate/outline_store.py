"""大纲缓存：同一份资料重复生成时复用章节结构。

发现：即使先出大纲，AI 每次给的章节划分也不同（8 章名字都不一样），
导致两次生成的内容几乎无法对齐。把大纲按「资料指纹」持久化后：
- 同一门课多次生成结构稳定，可逐章对比、逐章重生成；
- 省掉一次 API 调用。
设置 TERMFINALE_REFRESH_OUTLINE=1 可强制重算。
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from loguru import logger

from core import paths
from core.generate.outline import Chapter, Outline

OUTLINE_VERSION = "2026-11-08.3"  # 大纲提示词/章名清洗变更时递增，旧缓存自动失效


def fingerprint(materials: list[dict], lang: str, extra: str = "") -> str:
    """资料指纹：路径 + 大小 + 修改时间 + 范围/模式，避免内容或约束变了还复用旧大纲。"""
    digest = hashlib.sha1()
    for item in sorted(materials, key=lambda m: str(m.get("path", ""))):
        digest.update(str(item.get("path", "")).encode("utf-8", "ignore"))
        digest.update(str(item.get("size", "")).encode())
        digest.update(str(item.get("mtime", "")).encode())
    digest.update(OUTLINE_VERSION.encode())
    digest.update(str(lang).encode())
    if extra:
        digest.update(str(extra).encode("utf-8", "ignore"))
    return digest.hexdigest()[:16]


def _cache_file(key: str) -> Path:
    paths.ensure_dirs()
    folder = paths.debug_dir() / "outlines"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{key}.json"


def load(key: str) -> Outline | None:
    if os.getenv("TERMFINALE_REFRESH_OUTLINE", "").strip() in ("1", "true", "yes"):
        return None
    path = _cache_file(key)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        chapters = [Chapter(index=i, title=c["title"], pages=list(c["pages"]),
                            must_know=list(c.get("must_know", [])),
                            importance=int(c.get("importance", 3)),
                            est_words=int(c.get("est_words", 1800)))
                    for i, c in enumerate(data.get("chapters", []))]
        if not chapters:
            return None
        logger.info("复用已缓存的大纲：{} 章（{}）", len(chapters), key)
        return Outline(chapters, source="cached")
    except Exception as exc:  # noqa: BLE001
        logger.warning("大纲缓存读取失败: {}", exc)
        return None


def save(key: str, outline: Outline) -> None:
    try:
        payload = {
            "source": outline.source,
            "chapters": [
                {"title": c.title, "pages": c.pages, "must_know": c.must_know,
                 "importance": c.importance, "est_words": c.est_words}
                for c in outline.chapters
            ],
        }
        _cache_file(key).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("大纲缓存写入失败: {}", exc)
