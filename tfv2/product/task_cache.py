"""Task-level content cache: same source + same task = same result.

This is not an HTTP cache. It hashes the actual sections/source content, so a
changed page/task misses; unchanged materials never pay the model twice.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CACHE_VERSION = "v1"


def enabled() -> bool:
    import os
    return os.getenv("TFV2_TASK_CACHE", "1") != "0"


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()


def _cache_root() -> Path:
    from tfv2.product.data_paths import ARTIFACT_ROOT
    return ARTIFACT_ROOT.parent / "task_cache"


def cache_key(artifact_id: str, path: Path, kind: str, section_id: str,
              mode: str, count: int, gen_lang: str) -> str:
    parts = [CACHE_VERSION, artifact_id, kind, section_id, mode, str(count), gen_lang]
    parts.append(_hash_file(path / "sections.json"))
    source = path / "source"
    if source.is_dir():
        for f in sorted(source.iterdir()):
            if f.is_file():
                parts.append(f.name)
                parts.append(_hash_file(f))
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def load(key: str) -> dict | None:
    path = _cache_root() / f"{key}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def save(key: str, doc: dict) -> None:
    root = _cache_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{key}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
