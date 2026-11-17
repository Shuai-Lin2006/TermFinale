"""Consistent local backup for the packaged app.

The release build excludes the developer-only ``tools`` package, so the
user-facing backup endpoint cannot import ``tools.backup``. This module lives
with the product code and includes both the learning DB and the chat DB.
"""
from __future__ import annotations

import json
import os
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from tfv2.product.data_paths import DATA_ROOT


def _safe_copy_sqlite(src: Path, dst: Path) -> None:
    """Use SQLite's backup API so WAL pages are included consistently."""
    src_conn = sqlite3.connect(src)
    dst_conn = sqlite3.connect(dst)
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def backup(out_dir: Path, include_assets: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"termfinale-{stamp}.zip"
    tmp_product = out_dir / f".backup-product-{stamp}.sqlite3"
    tmp_chat = out_dir / f".backup-chat-{stamp}.sqlite3"
    product_db = DATA_ROOT / "product.sqlite3"
    try:
        from tfv2.store import DB_PATH as chat_db
    except Exception:
        chat_db = DATA_ROOT / "chat.sqlite3"
    if not product_db.is_file():
        raise FileNotFoundError("未找到学习数据库，无法备份")
    _safe_copy_sqlite(product_db, tmp_product)
    if Path(chat_db).is_file():
        _safe_copy_sqlite(Path(chat_db), tmp_chat)
    artifacts = []
    asset_files = 0
    for project in sorted((DATA_ROOT / "artifacts").glob("*/project.json")):
        try:
            artifacts.append({"id": project.parent.name, "project": project.read_text(encoding="utf-8")})
        except Exception:
            continue
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(tmp_product, "product.sqlite3")
            if tmp_chat.is_file():
                z.write(tmp_chat, "chat.sqlite3")
            z.writestr("artifacts.json", json.dumps(artifacts, ensure_ascii=False, indent=2))
            # A backup has to restore the things the DB points at, not only
            # the DB itself. Include generated lecture files and originals.
            for folder in ("artifacts", "uploads"):
                base = DATA_ROOT / folder
                if not base.is_dir():
                    continue
                for p in sorted(base.rglob("*")):
                    if not p.is_file() or p.name.startswith(".") or "__pycache__" in p.parts:
                        continue
                    z.write(p, str(p.relative_to(DATA_ROOT)))
                    asset_files += 1
            z.writestr("manifest.json", json.dumps({
                "created": stamp,
                "include_assets": True,
                "artifacts": len(artifacts),
                "asset_files": asset_files,
                "has_chat_db": tmp_chat.is_file(),
            }, ensure_ascii=False, indent=2))
    finally:
        tmp_product.unlink(missing_ok=True)
        tmp_chat.unlink(missing_ok=True)
    return path
