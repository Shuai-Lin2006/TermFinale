"""v3 产品持久化：练习/判分/错题/复习/设置/任务。

只存“学习行为”和用户设置；讲义内容仍以 artifact 目录为准。
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

from tfv2.product.data_paths import DATA_ROOT

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("TFV2_PRODUCT_DB", str(DATA_ROOT / "product.sqlite3")))


@contextmanager
def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS questions (
        id TEXT PRIMARY KEY,
        artifact_id TEXT NOT NULL,
        section TEXT NOT NULL,
        stem TEXT NOT NULL,
        options TEXT NOT NULL,
        answer INTEGER NOT NULL,
        explanation TEXT NOT NULL,
        page INTEGER,
        bank INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    try:
        conn.execute("ALTER TABLE questions ADD COLUMN bank INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.execute("""CREATE TABLE IF NOT EXISTS attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id TEXT NOT NULL,
        chosen INTEGER NOT NULL,
        correct INTEGER NOT NULL,
        context TEXT NOT NULL DEFAULT 'practice',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    try:
        conn.execute("ALTER TABLE attempts ADD COLUMN context TEXT NOT NULL DEFAULT 'practice'")
    except sqlite3.OperationalError:
        pass
    conn.execute("""CREATE TABLE IF NOT EXISTS mistakes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id TEXT NOT NULL UNIQUE,
        artifact_id TEXT NOT NULL,
        section TEXT NOT NULL,
        stem TEXT NOT NULL,
        options TEXT NOT NULL,
        answer INTEGER NOT NULL,
        explanation TEXT NOT NULL,
        page INTEGER,
        wrong_count INTEGER NOT NULL DEFAULT 1,
        stage INTEGER NOT NULL DEFAULT 0,
        next_review TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artifact_id TEXT NOT NULL,
        section TEXT,
        page INTEGER,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        artifact_id TEXT NOT NULL,
        section TEXT NOT NULL,
        title TEXT NOT NULL,
        status TEXT NOT NULL,
        issues TEXT NOT NULL,
        coverage TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS reviews (
        artifact_id TEXT PRIMARY KEY,
        reviewer TEXT NOT NULL,
        notes TEXT NOT NULL,
        reviewed_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS agent_workflows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        steps TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS agent_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS agent_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artifact_id TEXT NOT NULL DEFAULT '',
        goal TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS course_prefs (
        course_key TEXT PRIMARY KEY,
        target_score INTEGER NOT NULL DEFAULT 0,
        exam_date TEXT NOT NULL DEFAULT '',
        display_name TEXT NOT NULL DEFAULT '',
        credits INTEGER NOT NULL DEFAULT 0,
        course_type TEXT NOT NULL DEFAULT '',
        school_level TEXT NOT NULL DEFAULT '',
        difficulty INTEGER NOT NULL DEFAULT 3
    )""")
    for _col, _ddl in [
        ("display_name", "ALTER TABLE course_prefs ADD COLUMN display_name TEXT NOT NULL DEFAULT ''"),
        ("days_left", "ALTER TABLE course_prefs ADD COLUMN days_left INTEGER NOT NULL DEFAULT 7"),
        ("foundation", "ALTER TABLE course_prefs ADD COLUMN foundation TEXT NOT NULL DEFAULT '基础较弱'"),
        ("key_points", "ALTER TABLE course_prefs ADD COLUMN key_points TEXT NOT NULL DEFAULT ''"),
        ("excluded", "ALTER TABLE course_prefs ADD COLUMN excluded TEXT NOT NULL DEFAULT ''"),
        ("custom_prompt", "ALTER TABLE course_prefs ADD COLUMN custom_prompt TEXT NOT NULL DEFAULT ''"),
        ("mastery", "ALTER TABLE course_prefs ADD COLUMN mastery INTEGER NOT NULL DEFAULT 0"),
    ]:
        try:
            conn.execute(_ddl)
        except sqlite3.OperationalError:
            pass
    conn.execute("""CREATE TABLE IF NOT EXISTS ai_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        artifact_id TEXT NOT NULL DEFAULT '',
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        rating INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        status TEXT NOT NULL,
        progress INTEGER NOT NULL DEFAULT 0,
        step TEXT,
        error TEXT,
        result TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    # 轻量迁移：老库补列
    for table, col, ddl in [
        ("agent_goals", "next_run", "ALTER TABLE agent_goals ADD COLUMN next_run TEXT"),
        ("agent_goals", "last_run", "ALTER TABLE agent_goals ADD COLUMN last_run TEXT"),
        ("agent_goals", "enabled", "ALTER TABLE agent_goals ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1"),
        ("agent_goals", "auto", "ALTER TABLE agent_goals ADD COLUMN auto INTEGER NOT NULL DEFAULT 0"),
        ("agent_goals", "artifact_id", "ALTER TABLE agent_goals ADD COLUMN artifact_id TEXT NOT NULL DEFAULT ''"),
        ("agent_workflows", "version", "ALTER TABLE agent_workflows ADD COLUMN version INTEGER NOT NULL DEFAULT 1"),
        ("agent_memories", "embedding", "ALTER TABLE agent_memories ADD COLUMN embedding TEXT NOT NULL DEFAULT ''"),
        ("jobs", "payload", "ALTER TABLE jobs ADD COLUMN payload TEXT NOT NULL DEFAULT ''"),
        ("course_prefs", "credits", "ALTER TABLE course_prefs ADD COLUMN credits INTEGER NOT NULL DEFAULT 0"),
        ("course_prefs", "course_type", "ALTER TABLE course_prefs ADD COLUMN course_type TEXT NOT NULL DEFAULT ''"),
        ("course_prefs", "school_level", "ALTER TABLE course_prefs ADD COLUMN school_level TEXT NOT NULL DEFAULT ''"),
        ("course_prefs", "difficulty", "ALTER TABLE course_prefs ADD COLUMN difficulty INTEGER NOT NULL DEFAULT 3"),
        ("mistakes", "stability", "ALTER TABLE mistakes ADD COLUMN stability REAL NOT NULL DEFAULT 0"),
        ("mistakes", "difficulty", "ALTER TABLE mistakes ADD COLUMN difficulty REAL NOT NULL DEFAULT 5"),
        ("mistakes", "reps", "ALTER TABLE mistakes ADD COLUMN reps INTEGER NOT NULL DEFAULT 0"),
        ("mistakes", "lapses", "ALTER TABLE mistakes ADD COLUMN lapses INTEGER NOT NULL DEFAULT 0"),
        ("mistakes", "last_review", "ALTER TABLE mistakes ADD COLUMN last_review TEXT"),
    ]:
        try:
            cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if col not in cols:
                conn.execute(ddl)
        except Exception:
            pass
    conn.commit()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _rows(sql: str, args: tuple = ()) -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def _one(sql: str, args: tuple = ()) -> dict | None:
    with _conn() as c:
        row = c.execute(sql, args).fetchone()
        return dict(row) if row else None


# ---------------- questions / attempts / mistakes ----------------

def save_questions(items: list[dict], *, bank: bool = False) -> None:
    with _conn() as c:
        for q in items:
            c.execute(
                """INSERT OR REPLACE INTO questions
                   (id, artifact_id, section, stem, options, answer, explanation, page, bank)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (q["id"], q["artifact_id"], q["section"], q["stem"],
                 json.dumps(q["options"], ensure_ascii=False), int(q["answer"]),
                 q["explanation"], q.get("page"), 1 if (bank or q.get("bank")) else 0),
            )


def bank_questions(artifact_id: str, limit: int = 20) -> list[dict]:
    rows = _rows("SELECT * FROM questions WHERE artifact_id=? AND bank=1 ORDER BY id DESC LIMIT ?",
                 (artifact_id, max(1, min(limit, 100))))
    for r in rows:
        try:
            r["options"] = json.loads(r["options"])
        except Exception:
            r["options"] = []
    return rows


def delete_bank_question(qid: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM attempts WHERE question_id=?", (qid,))
        c.execute("DELETE FROM mistakes WHERE question_id=?", (qid,))
        c.execute("DELETE FROM questions WHERE id=? AND bank=1", (qid,))


def bank_questions_all(artifact_id: str) -> list[dict]:
    return bank_questions(artifact_id, limit=100)


def bank_counts() -> dict[str, int]:
    rows = _rows("SELECT artifact_id, COUNT(*) AS n FROM questions WHERE bank=1 GROUP BY artifact_id")
    return {str(r["artifact_id"]): int(r["n"]) for r in rows}


def get_question(qid: str) -> dict | None:
    row = _one("SELECT * FROM questions WHERE id=?", (qid,))
    if row:
        row["options"] = json.loads(row["options"])
    return row


def record_attempt(question_id: str, chosen: int, correct: bool, context: str = "practice") -> None:
    with _conn() as c:
        c.execute("INSERT INTO attempts(question_id,chosen,correct,context) VALUES(?,?,?,?)",
                  (question_id, int(chosen), 1 if correct else 0, context or "practice"))


def upsert_mistake(q: dict, *, review_in_days: int = 0) -> int:
    today = date.today()
    next_review = (today + timedelta(days=max(0, review_in_days))).isoformat()
    existing = _one("SELECT id FROM mistakes WHERE question_id=?", (q["id"],))
    with _conn() as c:
        if existing:
            c.execute(
                """UPDATE mistakes SET wrong_count=wrong_count+1, stage=0,
                   next_review=?, updated_at=datetime('now') WHERE id=?""",
                (next_review, existing["id"]),
            )
            return int(existing["id"])
        cur = c.execute(
            """INSERT INTO mistakes
               (question_id,artifact_id,section,stem,options,answer,explanation,page,next_review)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (q["id"], q["artifact_id"], q["section"], q["stem"],
             json.dumps(q["options"], ensure_ascii=False), int(q["answer"]),
             q["explanation"], q.get("page"), next_review),
        )
        return int(cur.lastrowid)


def due_mistakes(day: str | None = None) -> list[dict]:
    day = day or date.today().isoformat()
    rows = _rows("SELECT * FROM mistakes WHERE next_review<=? ORDER BY next_review,id", (day,))
    for r in rows:
        r["options"] = json.loads(r["options"])
    return rows


def all_mistakes() -> list[dict]:
    rows = _rows("SELECT * FROM mistakes ORDER BY next_review,id")
    for r in rows:
        r["options"] = json.loads(r["options"])
    return rows


def review_mistake(mid: int, remembered: bool) -> dict | None:
    row = _one("SELECT * FROM mistakes WHERE id=?", (mid,))
    if not row:
        return None
    from tfv2.product import fsrs

    today = date.today()
    state = fsrs.CardState(
        stability=float(row.get("stability") or 0.0),
        difficulty=float(row.get("difficulty") or 5.0),
        reps=int(row.get("reps") or 0),
        lapses=int(row.get("lapses") or 0),
        last_review=date.fromisoformat(str(row["last_review"])[:10]) if row.get("last_review") else None,
    )
    grade = fsrs.GRADE_GOOD if remembered else fsrs.GRADE_AGAIN
    new_state, days = fsrs.review(state, grade, today=today)
    next_review = (today + timedelta(days=days)).isoformat()
    stage = min(int(row["stage"]) + 1, 5) if remembered else 0
    with _conn() as c:
        c.execute(
            "UPDATE mistakes SET stage=?, next_review=?, stability=?, difficulty=?, reps=?, "
            "lapses=?, last_review=?, updated_at=datetime('now') WHERE id=?",
            (stage, next_review, new_state.stability, new_state.difficulty, new_state.reps,
             new_state.lapses, today.isoformat(), mid),
        )
    # 复习也是一次真实作答：写 Attempt，掌握度才能反映这次回忆。
    record_attempt(str(row["question_id"]), -1, bool(remembered), context="review")
    out = _one("SELECT * FROM mistakes WHERE id=?", (mid,))
    if out:
        out["options"] = json.loads(out["options"])
    return out


def mastery() -> list[dict]:
    rows = _rows(
        """SELECT q.artifact_id, q.section,
                  COUNT(a.id) AS attempts,
                  SUM(a.correct) AS correct
           FROM attempts a JOIN questions q ON q.id=a.question_id
           GROUP BY q.artifact_id, q.section
           ORDER BY q.artifact_id, q.section"""
    )
    for r in rows:
        r["attempts"] = int(r["attempts"] or 0)
        r["correct"] = int(r["correct"] or 0)
        r["accuracy"] = round(r["correct"] / r["attempts"], 3) if r["attempts"] else None
        # 拉普拉斯平滑，避免 1/1 被当成 100% 掌握；0 次就是无数据
        r["score"] = round((r["correct"] + 1) / (r["attempts"] + 2) * 100) if r["attempts"] else None
        r["confidence"] = round(min(1.0, r["attempts"] / 8), 2)
        if not r["attempts"]:
            r["label"] = "no_data"
        elif r["attempts"] < 3:
            r["label"] = "learning"
        elif (r["score"] or 0) >= 80 and r["confidence"] >= 0.5:
            r["label"] = "strong"
        elif (r["score"] or 0) < 60:
            r["label"] = "weak"
        else:
            r["label"] = "learning"
    return rows


# ---------------- notes / settings / jobs ----------------

def save_note(artifact_id: str, text: str, *, section: str = "", page: int | None = None) -> int:
    with _conn() as c:
        cur = c.execute("INSERT INTO notes(artifact_id,section,page,text) VALUES(?,?,?,?)",
                        (artifact_id, section or "", page, text.strip()))
        return int(cur.lastrowid)


def list_notes(artifact_id: str | None = None) -> list[dict]:
    if artifact_id:
        return _rows("SELECT * FROM notes WHERE artifact_id=? ORDER BY id DESC", (artifact_id,))
    return _rows("SELECT * FROM notes ORDER BY id DESC")


def delete_note(note_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM notes WHERE id=?", (note_id,))


def get_setting(key: str, default: str = "") -> str:
    row = _one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def has_setting(key: str) -> bool:
    return _one("SELECT value FROM settings WHERE key=?", (key,)) is not None


def set_setting(key: str, value: str) -> None:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))


# ---------------- reviews ----------------

def save_review(artifact_id: str, reviewer: str, notes: str) -> dict:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO reviews(artifact_id,reviewer,notes) VALUES(?,?,?)",
                  (artifact_id, reviewer.strip()[:40], notes.strip()[:1000]))
    return get_review(artifact_id) or {}


def get_review(artifact_id: str) -> dict | None:
    return _one("SELECT * FROM reviews WHERE artifact_id=?", (artifact_id,))


# ---------------- documents ----------------

def save_document(doc: dict) -> str:
    did = doc.get("id") or uuid.uuid4().hex
    with _conn() as c:
        c.execute(
            """INSERT OR REPLACE INTO documents
               (id,kind,artifact_id,section,title,status,issues,coverage,content)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (did, doc.get("kind", ""), doc.get("artifact_id", ""), doc.get("section", ""),
             doc.get("title", ""), doc.get("status", "rejected"),
             json.dumps(doc.get("issues") or [], ensure_ascii=False),
             json.dumps(doc.get("coverage") or {}, ensure_ascii=False),
             json.dumps(doc.get("content") or {}, ensure_ascii=False)),
        )
    return did


def list_documents(limit: int = 50) -> list[dict]:
    rows = _rows("SELECT * FROM documents ORDER BY created_at DESC, id DESC LIMIT ?", (max(1, min(limit, 200)),))
    for r in rows:
        for key in ("issues", "coverage", "content"):
            try:
                r[key] = json.loads(r[key])
            except Exception:
                r[key] = [] if key == "issues" else {}
    return rows


def get_document(did: str) -> dict | None:
    row = _one("SELECT * FROM documents WHERE id=?", (did,))
    if row:
        for key in ("issues", "coverage", "content"):
            try:
                row[key] = json.loads(row[key])
            except Exception:
                row[key] = [] if key == "issues" else {}
    return row


def rename_document(did: str, title: str) -> None:
    with _conn() as c:
        c.execute("UPDATE documents SET title=? WHERE id=?", (str(title or "").strip()[:160], did))


def delete_document(did: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM documents WHERE id=?", (did,))


# ---------------- jobs ----------------

def create_job(job_id: str, kind: str, payload: dict | None = None) -> None:
    import json
    with _conn() as c:
        c.execute("INSERT INTO jobs(id,kind,status,progress,step,payload) VALUES(?,?,?,?,?,?)",
                  (job_id, kind, "running", 0, "排队", json.dumps(payload or {}, ensure_ascii=False)))


def update_job(job_id: str, **fields) -> None:
    allowed = {"status", "progress", "step", "error", "result", "payload"}
    sets = [f"{k}=?" for k in fields if k in allowed]
    args = [fields[k] for k in fields if k in allowed]
    if not sets:
        return
    with _conn() as c:
        c.execute(f"UPDATE jobs SET {','.join(sets)},updated_at=datetime('now') WHERE id=?",
                  (*args, job_id))


def save_ai_feedback(artifact_id: str, question: str, answer: str, rating: int) -> None:
    with _conn() as c:
        c.execute("INSERT INTO ai_feedback(artifact_id,question,answer,rating) VALUES(?,?,?,?)",
                  (artifact_id, question[:1000], answer[:2000], 1 if rating > 0 else -1))




def delete_course_records(course_key: str, artifact_ids: list[str]) -> int:
    """课程删除时清理本机关联记录；讲义文件由 service 移到 archive。"""
    ids = [str(x) for x in artifact_ids if str(x)]
    if not ids:
        return 0
    marks = ",".join("?" for _ in ids)
    with _conn() as c:
        qids = [r[0] for r in c.execute(f"SELECT id FROM questions WHERE artifact_id IN ({marks})", ids).fetchall()]
        removed = 0
        if qids:
            qmarks = ",".join("?" for _ in qids)
            c.execute(f"DELETE FROM attempts WHERE question_id IN ({qmarks})", qids)
            removed += c.execute(f"DELETE FROM questions WHERE id IN ({qmarks})", qids).rowcount
        c.execute(f"DELETE FROM mistakes WHERE artifact_id IN ({marks})", ids)
        c.execute(f"DELETE FROM documents WHERE artifact_id IN ({marks})", ids)
        c.execute(f"DELETE FROM notes WHERE artifact_id IN ({marks})", ids)
        c.execute(f"DELETE FROM agent_memories WHERE artifact_id IN ({marks})", ids)
        c.execute(f"DELETE FROM reviews WHERE artifact_id IN ({marks})", ids)
        c.execute("DELETE FROM course_prefs WHERE course_key=?", (course_key,))
    try:
        from tfv2.store import clear_artifacts_chat
        clear_artifacts_chat(ids)
    except Exception:
        # The learning DB is authoritative; a chat cleanup failure must not
        # turn a completed course deletion into a misleading 500.
        pass
    return removed


def get_course_prefs(key: str) -> dict:
    row = _one("SELECT * FROM course_prefs WHERE course_key=?", (key,))
    base = {"course_key": key, "target_score": 0, "exam_date": "", "display_name": "",
            "credits": 0.5, "course_type": "", "school_level": "", "difficulty": 3,
            "days_left": 7, "foundation": "基础较弱", "key_points": "",
            "excluded": "", "custom_prompt": "", "mastery": 0}
    if row:
        base.update(dict(row))
    return base


def save_course_prefs(key: str, target_score: int, exam_date: str, display_name: str = "",
                      credits: int = 0, course_type: str = "", school_level: str = "",
                      difficulty: int = 3, *, days_left: int | None = None,
                      foundation: str = "", key_points: str = "", excluded: str = "",
                      custom_prompt: str = "", mastery: int = 0) -> dict:
    with _conn() as c:
        c.execute("INSERT INTO course_prefs(course_key,target_score,exam_date,display_name,credits,course_type,school_level,difficulty,days_left,foundation,key_points,excluded,custom_prompt,mastery) "
                  "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                  "ON CONFLICT(course_key) DO UPDATE SET target_score=excluded.target_score, exam_date=excluded.exam_date, "
                  "display_name=excluded.display_name, credits=excluded.credits, course_type=excluded.course_type, "
                  "school_level=excluded.school_level, difficulty=excluded.difficulty, days_left=excluded.days_left, "
                  "foundation=excluded.foundation, key_points=excluded.key_points, excluded=excluded.excluded, "
                  "custom_prompt=excluded.custom_prompt, mastery=excluded.mastery",
                  (key, max(60, min(100, int(target_score))), exam_date[:10], str(display_name or "").strip()[:80],
                   max(0.5, min(10.0, float(credits or 0.5))), str(course_type or "").strip()[:30],
                   str(school_level or "").strip()[:30], max(1, min(5, int(difficulty or 3))),
                   max(1, min(30, int(days_left if days_left is not None else 7))),
                   str(foundation or "基础较弱"), str(key_points or ""), str(excluded or ""),
                   str(custom_prompt or ""), max(0, min(5, int(mastery or 0)))))
    return get_course_prefs(key)


def save_workflow(name: str, steps: list[dict]) -> dict:
    name = name.strip()[:80]
    with _conn() as c:
        row = c.execute("SELECT COALESCE(MAX(version),0)+1 FROM agent_workflows WHERE name=?", (name,)).fetchone()
        version = int(row[0] or 1)
        cur = c.execute("INSERT INTO agent_workflows(name,steps,version) VALUES(?,?,?)",
                        (name, json.dumps(steps, ensure_ascii=False), version))
    return {"id": int(cur.lastrowid), "name": name, "steps": steps, "version": version}


def list_workflows(limit: int = 20) -> list[dict]:
    rows = _rows("SELECT * FROM agent_workflows ORDER BY id DESC LIMIT ?", (int(limit),))
    for r in rows:
        try: r["steps"] = json.loads(r["steps"])
        except Exception: r["steps"] = []
    return rows


def get_workflow(wid: int) -> dict | None:
    row = _one("SELECT * FROM agent_workflows WHERE id=?", (int(wid),))
    if row:
        try: row["steps"] = json.loads(row["steps"])
        except Exception: row["steps"] = []
    return row


def workflow_diff(wid: int, against: int) -> dict | None:
    import difflib
    a, b = get_workflow(against), get_workflow(wid)
    if not a or not b:
        return None
    left = json.dumps(a.get("steps") or [], ensure_ascii=False, indent=2).splitlines()
    right = json.dumps(b.get("steps") or [], ensure_ascii=False, indent=2).splitlines()
    return {"left": a, "right": b, "diff": "\n".join(difflib.unified_diff(left, right, fromfile=f"v{a.get('version')}", tofile=f"v{b.get('version')}", lineterm=""))}


def save_goal(goal: str, *, next_run: str | None = None, auto: bool = False, artifact_id: str = "") -> dict:
    from datetime import date
    next_run = next_run or date.today().isoformat()
    with _conn() as c:
        cur = c.execute("INSERT INTO agent_goals(goal,next_run,auto,artifact_id) VALUES(?,?,?,?)",
                        (goal.strip()[:800], next_run, 1 if auto else 0, artifact_id))
    return {"id": int(cur.lastrowid), "goal": goal.strip()[:800], "status": "active",
            "next_run": next_run, "auto": bool(auto), "artifact_id": artifact_id}


def list_goals(limit: int = 20) -> list[dict]:
    return _rows("SELECT * FROM agent_goals ORDER BY id DESC LIMIT ?", (int(limit),))


def due_goals(day: str | None = None) -> list[dict]:
    from datetime import date
    day = day or date.today().isoformat()
    return _rows("SELECT * FROM agent_goals WHERE enabled=1 AND COALESCE(next_run,'')<=? ORDER BY next_run,id", (day,))


def due_auto_goals(day: str | None = None) -> list[dict]:
    from datetime import date
    day = day or date.today().isoformat()
    return _rows("SELECT * FROM agent_goals WHERE enabled=1 AND auto=1 AND COALESCE(next_run,'')<=? ORDER BY next_run,id", (day,))


def advance_goal(gid: int, days: int = 1) -> dict | None:
    from datetime import date, timedelta
    row = _one("SELECT * FROM agent_goals WHERE id=?", (int(gid),))
    if not row:
        return None
    nxt = (date.today() + timedelta(days=max(1, min(365, int(days))))).isoformat()
    with _conn() as c:
        c.execute("UPDATE agent_goals SET last_run=?,next_run=? WHERE id=?", (date.today().isoformat(), nxt, int(gid)))
    return _one("SELECT * FROM agent_goals WHERE id=?", (int(gid),))


def _embed_hash(text: str, dim: int = 128) -> list[float]:
    """轻量字符 bigram 哈希向量；API 不可用时的回退。"""
    import hashlib, math
    vec = [0.0] * dim
    t = (text or "").lower()
    for i in range(max(1, len(t) - 1)):
        g = t[i:i + 2]
        h = int(hashlib.md5(g.encode("utf-8")).hexdigest()[:8], 16)
        vec[h % dim] += 1.0
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


def _embed(text: str, dim: int = 128) -> list[float]:
    import os
    if os.getenv("TERMFINALE_EMBEDDING", "").lower() == "api":
        try:
            from dashscope import TextEmbedding
            from core.config import get_key, load_env
            load_env()
            r = TextEmbedding.call(model="text-embedding-v4", input=text[:1800], api_key=get_key("DASHSCOPE_API_KEY"))
            if getattr(r, "status_code", 0) == 200:
                return [float(x) for x in r.output["embeddings"][0]["embedding"]]
        except Exception:
            pass
    return _embed_hash(text, dim)


def _cos(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def save_memory(goal: str, content: str, artifact_id: str = "") -> int:
    import json
    emb = json.dumps(_embed(goal + " " + content), ensure_ascii=False)
    with _conn() as c:
        cur = c.execute("INSERT INTO agent_memories(artifact_id,goal,content,embedding) VALUES(?,?,?,?)",
                        (artifact_id, goal[:200], content[:1200], emb))
        return int(cur.lastrowid)


def list_memories(limit: int = 20, artifact_id: str = "") -> list[dict]:
    with _conn() as c:
        if artifact_id:
            rows = c.execute("SELECT * FROM agent_memories WHERE artifact_id=? ORDER BY id DESC LIMIT ?",
                             (artifact_id, limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM agent_memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def recall_memory(goal: str, artifact_id: str = "", limit: int = 3) -> list[str]:
    import json
    q = _embed(goal)
    scored = []
    for row in list_memories(limit=50, artifact_id=artifact_id):
        try:
            emb = json.loads(row.get("embedding") or "[]")
        except Exception:
            emb = []
        if not emb or len(emb) != len(q):
            emb = _embed((row.get("goal") or "") + " " + (row.get("content") or ""))
        score = _cos(q, emb) if emb else 0.0
        if goal and goal in (row.get("goal") or ""):
            score += 0.15
        if score > 0.05:
            scored.append((score, row.get("content") or ""))
    scored.sort(reverse=True)
    return [text for _, text in scored[:limit]]


def mark_interrupted_jobs() -> int:
    """服务重启后，遗留 running 任务标中断，避免永久卡 running。"""
    with _conn() as c:
        cur = c.execute("UPDATE jobs SET status='failed', error=?, step='服务重启中断', updated_at=datetime('now') WHERE status='running'",
                        ("服务重启，任务未完成；请重新发起",))
        return int(cur.rowcount)


def list_jobs(kind: str = "", limit: int = 20) -> list[dict]:
    if kind:
        rows = _rows("SELECT * FROM jobs WHERE kind=? ORDER BY created_at DESC,id DESC LIMIT ?", (kind, int(limit)))
    else:
        rows = _rows("SELECT * FROM jobs ORDER BY created_at DESC,id DESC LIMIT ?", (int(limit),))
    for row in rows:
        if row.get("result"):
            try:
                row["result"] = json.loads(row["result"])
            except Exception:
                pass
    return rows


def get_job(job_id: str) -> dict | None:
    row = _one(
        "SELECT *, MAX(0, CAST(strftime('%s','now') AS INTEGER) - CAST(strftime('%s',created_at) AS INTEGER)) AS elapsed_s "
        "FROM jobs WHERE id=?", (job_id,))
    if row and row.get("result"):
        try:
            row["result"] = json.loads(row["result"])
        except Exception:
            pass
    return row


def delete_artifact_records(artifact_id: str) -> int:
    """Remove learner records for one lecture without deleting course prefs."""
    aid = str(artifact_id or "").strip()
    if not aid:
        return 0
    with _conn() as c:
        qids = [r[0] for r in c.execute("SELECT id FROM questions WHERE artifact_id=?", (aid,)).fetchall()]
        if qids:
            marks = ",".join("?" for _ in qids)
            c.execute(f"DELETE FROM attempts WHERE question_id IN ({marks})", qids)
            c.execute(f"DELETE FROM questions WHERE id IN ({marks})", qids)
        c.execute("DELETE FROM mistakes WHERE artifact_id=?", (aid,))
        c.execute("DELETE FROM documents WHERE artifact_id=?", (aid,))
        c.execute("DELETE FROM notes WHERE artifact_id=?", (aid,))
        c.execute("DELETE FROM agent_memories WHERE artifact_id=?", (aid,))
        c.execute("DELETE FROM reviews WHERE artifact_id=?", (aid,))
    try:
        from tfv2.store import clear_artifacts_chat
        clear_artifacts_chat([aid])
    except Exception:
        pass
    return 0


def review_due(limit: int = 50) -> list[dict]:
    """今天到期的错题，按逾期→稳定性低排序（用于复习页）。"""
    from tfv2.product import fsrs

    rows = all_mistakes()
    return fsrs.due_cards(rows, today=date.today(), limit=limit)


def review_forecast(days: int = 7) -> list[dict]:
    from tfv2.product import fsrs

    return fsrs.forecast(all_mistakes(), today=date.today(), days=days)
