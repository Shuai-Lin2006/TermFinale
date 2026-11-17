"""v2 本地持久化：聊天会话（跨刷新/跨会话），SQLite。"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from tfv2.product.data_paths import DATA_ROOT

ROOT = Path(__file__).resolve().parents[1]
_LEGACY_DB = ROOT / "data" / "v2.sqlite3"
DB_PATH = Path(os.getenv("TFV2_DB", str(DATA_ROOT / "chat.sqlite3")))
# One-time migration: older builds wrote chat history inside the app bundle.
if not os.getenv("TFV2_DB") and not DB_PATH.exists() and _LEGACY_DB.is_file():
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_LEGACY_DB, DB_PATH)
    except Exception:
        pass


@contextmanager
def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artifact_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat ON chat_messages(artifact_id, session_id, id)")
    try:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN meta TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def append_chat(artifact_id: str, session_id: str, role: str, content: str, meta: str = "") -> None:
    if role not in ("user", "assistant") or not content.strip():
        return
    with _conn() as c:
        c.execute("INSERT INTO chat_messages(artifact_id,session_id,role,content,meta) VALUES(?,?,?,?,?)",
                  (artifact_id, session_id or "default", role, content.strip(), (meta or "")[:12000]))


def list_chat(artifact_id: str, session_id: str = "default", limit: int = 200) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT role,content,created_at,meta FROM chat_messages WHERE artifact_id=? AND session_id=? ORDER BY id DESC LIMIT ?",
            (artifact_id, session_id or "default", max(1, min(limit, 500))),
        ).fetchall()
    out = []
    for r, x, t, meta in reversed(rows):
        item = {"role": r, "content": x, "created_at": t}
        if meta:
            item["meta"] = meta
        out.append(item)
    return out


def clear_chat(artifact_id: str, session_id: str = "default") -> None:
    with _conn() as c:
        c.execute("DELETE FROM chat_messages WHERE artifact_id=? AND session_id=?",
                  (artifact_id, session_id or "default"))


def clear_artifacts_chat(artifact_ids: list[str]) -> None:
    """Delete chat sessions for a set of artifacts from the chat DB."""
    ids = [str(x) for x in artifact_ids if str(x)]
    if not ids:
        return
    marks = ",".join("?" for _ in ids)
    with _conn() as c:
        c.execute(f"DELETE FROM chat_messages WHERE artifact_id IN ({marks})", ids)
