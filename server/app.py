"""TermFinale 本地 API：给新 Web UI 提供课程、生成任务、问答与设置。

启动：python server/app.py    （默认 127.0.0.1:8900）
"""
from __future__ import annotations

import asyncio
import json
import datetime
import os
import re
import hashlib
import secrets
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))

from core import config, paths  # noqa: E402
from core.database import (  # noqa: E402
    Course, GeneratedFile, Material, Mistake, Note, Profile,
    get_db_session, init_db, looks_like_test_course,
)
from core.logger import install_exception_hooks, setup_logging  # noqa: E402
from sqlalchemy import or_  # noqa: E402
from core.parser import PARSER_VERSION, extract_text_from_file  # noqa: E402
from services import guide_service, review_service  # noqa: E402
from core.quality.report import audit_markdown
from core.quality.constraints import TaskConstraints, scope_pages  # noqa: E402
from core.quality.gate import ConstraintViolation  # noqa: E402
from services.task import ProgressEvent  # noqa: E402

WEB = ROOT / "web"
setup_logging()
install_exception_hooks()

# 本地 API 鉴权：页面首次加载时下发 HttpOnly SameSite=Strict cookie；
# 跨站请求不会带 cookie，恶意网页无法读课程/清库/烧 Key。
# token 持久化到数据目录（0600）：重启后端后旧页面不用重新拿 cookie。
def _load_or_create_token() -> str:
    try:
        paths.ensure_dirs()
        token_file = paths.data_dir() / ".session_token"
        if token_file.is_file():
            token = token_file.read_text(encoding="utf-8").strip()
            if len(token) >= 20:
                return token
        token = secrets.token_urlsafe(24)
        token_file.write_text(token, encoding="utf-8")
        try:
            token_file.chmod(0o600)
        except OSError:
            pass
        return token
    except Exception:
        return secrets.token_urlsafe(24)


_AUTH_TOKEN = _load_or_create_token()
_DISABLE_AUTH = os.getenv("TERMFINALE_DISABLE_AUTH", "").strip().lower() in ("1", "true", "yes")
_PORT = int(os.getenv("TERMFINALE_WEB_PORT", "8900"))
_ALLOWED_ORIGINS = [f"http://127.0.0.1:{_PORT}", f"http://localhost:{_PORT}"]

app = FastAPI(title="TermFinale API", version="0.3.0")
init_db()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

JOBS: dict[str, "Job"] = {}
JOBS_LOCK = threading.Lock()


class Job:
    def __init__(self, task: str):
        self.id = uuid.uuid4().hex[:12]
        self.task = task
        self.status = "running"
        self.progress = 0.0
        self.message = "准备中…"
        self.events: list[dict] = []
        self.result: dict | None = None
        self.error: str | None = None
        self.stop = threading.Event()
        self.started = time.time()

    def emit(self, event: ProgressEvent) -> None:
        self.progress = max(0.0, min(1.0, event.value))
        self.message = event.message
        with JOBS_LOCK:
            self.events.append({"t": round(time.time() - self.started, 1),
                                "progress": self.progress, "message": event.message})

    def snapshot(self) -> dict:
        return {"id": self.id, "task": self.task, "status": self.status,
                "progress": self.progress, "message": self.message,
                "elapsed": round(time.time() - self.started, 1),
                "eta": (round((time.time() - self.started) * (1 - self.progress) / self.progress, 1)
                        if self.progress > 0.05 else None),
                "result": self.result, "error": self.error}


def _safe_days_left(course: Course) -> int:
    """exam_date 是用户可编辑的字符串；一个坏值不能让整个课程列表 500。"""
    try:
        raw = getattr(course, "exam_date", "") or ""
        if raw:
            return max(0, (datetime.date.fromisoformat(str(raw)[:10]) - datetime.date.today()).days)
    except (ValueError, TypeError):
        pass
    return int(getattr(course, "days_left", 0) or 0)


def _course_dict(course: Course) -> dict:
    return {"id": course.id, "name": course.name, "major": course.major,
            "school": course.school_level, "credits": course.credits,
            "days_left": _safe_days_left(course), "target_score": course.target_score,
            "difficulty": getattr(course, "self_difficulty", None) or course.user_difficulty,
            "foundation": getattr(course, "foundation", None) or 3,
            "is_major": course.is_major,
            "is_test": bool(getattr(course, "is_test", False)),
            "persona": course.persona or "温柔小姐姐"}


def _not_test_filter():
    """兼容老库的 NULL：未标记的课程按正式课程处理。"""
    return or_(Course.is_test.is_(None), Course.is_test == False)  # noqa: E712




import re as _re
import html as _html
import markdown as _markdown
from urllib.parse import quote as _quote


def _render_markdown(md: str) -> tuple[str, list[dict]]:
    """把讲义 Markdown 转成阅读器 HTML（数学公式保留给 KaTeX 客户端渲染）。"""
    def _fig(m):
        name = m.group(1).strip()
        if not (paths.assets_dir() / name).is_file():
            return "\n\n"
        caption = _html.escape(m.group(2).strip(), quote=True)
        return (f'\n\n<figure class="figure"><img src="/api/assets/{_quote(name)}"'
                f' alt="{caption}"><figcaption>{caption}</figcaption></figure>\n\n')
    md = _re.sub(r"\[\[\[IMAGE:\s*([^|\]]+?)\s*\|\s*图注:\s*(.*?)\]\]\]",
                 _fig, md)
    md = _re.sub(r"\[\[([^|\]]+?)\|([^\]]+?)\]\]",
                 lambda m: (f'<span class="kw" title="{_html.escape(m.group(2).strip(), quote=True)}">'
                            f'{_html.escape(m.group(1).strip())}</span>'), md)

    # 选项 A/B/C/D 强制换行（Markdown 默认会把单换行合并成空格）
    md = _re.sub(r"(?m)^(.*?)\n(?=[A-D]\s*[.、．)])", r"\1  \n", md)
    md = _re.sub(r"(?m)^([A-D])\s*([.、．)])\s*(.+?)\s*$", r"\1\2 \3  ", md)

    # 与 exporter 对齐：先把 \(...\) / \[...\] 归一成 $...$，否则 Markdown 会吃掉反斜杠
    md = _re.sub(r"\\\[(.*?)\\\]", r"$$\1$$", md, flags=_re.S)
    md = _re.sub(r"\\\((.*?)\\\)", r"$\1$", md, flags=_re.S)

    math: list[str] = []
    def stash(m):
        math.append(m.group(0))
        return f"@@MATH{len(math) - 1}@@"
    md = _re.sub(r"(\$\$.*?\$\$|\$[^$\n]+?\$)", stash, md, flags=_re.S)
    html = _markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    for i, tex in enumerate(math):
        # 公式最后塞回，必须转义 & < >（同 exporter.py）
        html = html.replace(f"@@MATH{i}@@", _html.escape(tex, quote=False))

    toc = []
    chapter_no = 0
    def tag(m):
        nonlocal chapter_no
        level, raw = m.group(1), m.group(2)
        text = _re.sub(r"<[^>]+>", "", raw)
        anchor = f"h{len(toc)}"
        toc.append({"level": level, "text": text, "id": anchor})
        body = raw
        if level == "2":
            m2 = _re.match(r"\s*(?:核心考点|核心考點|Core Concept)[:：]\s*(.*)", text)
            if m2:
                chapter_no += 1
                body = f'<span class="chap-no">第 {chapter_no} 章</span>{m2.group(1)}'
        return f'<h{level} id="{anchor}">{body}</h{level}>'
    html = _re.sub(r"<h([23])>(.*?)</h\1>", tag, html, flags=_re.S)
    html = _re.sub(r'<blockquote>\s*<p>(📌 出处[^<]*)</p>\s*</blockquote>',
                   r'<div class="meta-info">\1</div>', html)
    html = _re.sub(r'<p><strong>(例\s*[0-9一二三四五六七八九十][^<]*)</strong>(.*?)</p>',
                   r'<div class="example"><div class="ex-label">\1</div>\2</div>', html, flags=_re.S)
    return html, toc

@app.middleware("http")
async def no_store_html(request, call_next):
    response = await call_next(request)
    if request.url.path.endswith(".html") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-store, max-age=0"
        # 首次打开页面时下发会话 cookie；JS 不读它，浏览器自动随同源 fetch 发送
        if not _DISABLE_AUTH:
            response.set_cookie("tf_token", _AUTH_TOKEN, httponly=True,
                                samesite="strict", max_age=7 * 24 * 3600, path="/")
    return response


@app.middleware("http")
async def require_local_token(request, call_next):
    path = request.url.path
    origin = request.headers.get("origin")
    # 跨站 Origin 一律拒绝（同源页面不会带 evil Origin；Electron 走 127.0.0.1）
    if origin and origin not in _ALLOWED_ORIGINS and request.method != "OPTIONS":
        return JSONResponse({"detail": "origin not allowed"}, status_code=403)

    if path.startswith("/api/") and path != "/api/health" and not _DISABLE_AUTH:
        token = request.headers.get("X-TF-Token") or request.cookies.get("tf_token")
        if token != _AUTH_TOKEN:
            return JSONResponse({"detail": "forbidden: missing or invalid token"}, status_code=403)

    return await call_next(request)


@app.get("/api/health")
def health():
    return {"ok": True, "time": time.strftime("%Y-%m-%d %H:%M")}


@app.get("/api/courses")
def list_courses(include_test: bool = False):
    db = get_db_session()
    try:
        q = db.query(Course)
        if not include_test:
            q = q.filter(_not_test_filter())
        out = []
        for c in q.order_by(Course.days_left.asc()).all():
            out.append({**_course_dict(c),
                        "materials": len(c.materials),
                        "materials_ok": sum(1 for m in c.materials if Path(m.file_path).exists()),
                        "generated": len(c.generated_files)})
        return out
    finally:
        db.close()




ALLOWED_UPLOAD = {".pdf", ".pptx", ".docx", ".txt", ".md", ".jpg", ".jpeg", ".png", ".webp",
                  ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".amr"}
MAX_UPLOAD_MB = 500


@app.post("/api/courses/{course_id}/materials")
async def upload_material(course_id: int, file: UploadFile = File(...)):
    db = get_db_session()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(404, "课程不存在")
        name = Path(file.filename or "upload").name
        ext = Path(name).suffix.lower()
        if ext not in ALLOWED_UPLOAD:
            raise HTTPException(400, f"不支持的文件类型：{ext or '未知'}")

        target_dir = paths.data_dir() / "uploads" / str(course_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / name
        stem, n = target.stem, 1
        while target.exists():
            target = target_dir / f"{stem}_{n}{ext}"
            n += 1

        size = 0
        with target.open("wb") as out:
            while True:
                chunk = await file.read(1 << 20)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_MB * 1024 * 1024:
                    out.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(400, f"文件超过 {MAX_UPLOAD_MB}MB")
                out.write(chunk)

        material = Material(course_id=course_id, file_path=str(target),
                            file_type="core", filename=name)
        db.add(material)
        db.commit()
        return {"id": material.id, "filename": name, "size_kb": round(size / 1024),
                "type": ext.lstrip(".")}
    finally:
        db.close()


@app.patch("/api/materials/{material_id}")
def update_material(material_id: int, payload: dict):
    db = get_db_session()
    try:
        m = db.query(Material).filter(Material.id == material_id).first()
        if not m:
            raise HTTPException(404, "资料不存在")
        if payload.get("role") in ("core", "support"):
            m.file_type = payload["role"]
        if payload.get("weight") is not None:
            m.weight = max(1, min(5, int(payload["weight"])))
        db.commit()
        return {"id": m.id, "role": m.file_type, "weight": m.weight}
    finally:
        db.close()


@app.delete("/api/courses/{course_id}/materials/{material_id}")
def delete_material(course_id: int, material_id: int):
    db = get_db_session()
    try:
        m = db.query(Material).filter(Material.id == material_id,
                                      Material.course_id == course_id).first()
        if not m:
            raise HTTPException(404, "资料不存在")
        db.delete(m)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.get("/api/overview")
def overview(include_test: bool = False):
    courses = list_courses(include_test=include_test)
    db = get_db_session()
    try:
        q = (db.query(GeneratedFile, Course)
             .join(Course, GeneratedFile.course_id == Course.id))
        if not include_test:
            q = q.filter(_not_test_filter())
        rows = q.order_by(GeneratedFile.id.desc()).limit(6).all()
        recent = []
        for gen, course in rows:
            path = Path(gen.file_path)
            recent.append({"course": course.name, "course_id": course.id, "file_id": gen.id,
                           "filename": path.name, "type": gen.file_type,
                           "exists": path.is_file(),
                           "has_md": path.with_suffix(".md").is_file()})
        materials = sum(c["materials"] for c in courses)
        nearest = min((c["days_left"] for c in courses), default=None)
        top = sorted(courses, key=lambda c: (c["days_left"], -c["generated"]))[:1]
        return {"courses": courses, "recent": recent,
                "stats": {"courses": len(courses), "materials": materials,
                          "nearest": nearest, "focus": top[0] if top else None}}
    finally:
        db.close()


def _normalize_exam_date(value) -> str:
    if not value:
        return ""
    try:
        return datetime.date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:
        raise HTTPException(400, "考试日期格式应为 YYYY-MM-DD")


@app.post("/api/courses")
def create_course(payload: dict):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "课程名不能为空")
    major = (payload.get("major") or "未知")[:100]
    db = get_db_session()
    try:
        days = max(1, int(payload.get("days_left") or 7))
        exam_date = _normalize_exam_date(payload.get("exam_date")) or (
            datetime.date.today() + datetime.timedelta(days=days)).isoformat()
        c = Course(
            name=name[:100],
            major=major,
            school_level=payload.get("school_level") or "一本",
            credits=max(0.5, min(8.0, float(payload.get("credits") or 3))),
            days_left=days,
            exam_date=exam_date,
            target_score=max(0, min(100, int(payload.get("target_score") or 80))),
            user_difficulty=max(1, min(5, int(payload.get("self_difficulty") or payload.get("user_difficulty") or 3))),
            self_difficulty=max(1, min(5, int(payload.get("self_difficulty") or payload.get("user_difficulty") or 3))),
            foundation=max(1, min(5, int(payload.get("foundation") or 3))),
            is_major=bool(payload.get("is_major", True)),
            is_test=bool(payload.get("is_test")) or looks_like_test_course(name, major),
            persona=payload.get("persona") or "温柔小姐姐",
        )
        db.add(c); db.commit()
        return _course_dict(c)
    finally:
        db.close()


@app.patch("/api/courses/{course_id}")
def update_course(course_id: int, payload: dict):
    db = get_db_session()
    try:
        c = db.query(Course).filter(Course.id == course_id).first()
        if not c:
            raise HTTPException(404, "课程不存在")
        for field, cast in (("name", str), ("major", str), ("school_level", str),
                            ("credits", float), ("days_left", int), ("target_score", int),
                            ("user_difficulty", int), ("self_difficulty", int), ("foundation", int)):
            if payload.get(field) not in (None, ""):
                value = cast(payload[field])
                if field == "credits":
                    value = max(0.5, min(8.0, float(value)))
                setattr(c, field, value)
        if payload.get("exam_date"):
            c.exam_date = _normalize_exam_date(payload["exam_date"])
        elif payload.get("days_left") not in (None, ""):
            days = int(payload.get("days_left") or 7)
            c.exam_date = (datetime.date.today() + datetime.timedelta(days=max(1, days))).isoformat()
        if "is_major" in payload:
            c.is_major = bool(payload["is_major"])
        if "is_test" in payload:
            c.is_test = bool(payload["is_test"])
        if payload.get("persona"):
            c.persona = payload["persona"]
        db.commit()
        return _course_dict(c)
    finally:
        db.close()


@app.delete("/api/courses/{course_id}")
def delete_course(course_id: int):
    db = get_db_session()
    try:
        c = db.query(Course).filter(Course.id == course_id).first()
        if not c:
            raise HTTPException(404, "课程不存在")
        db.delete(c); db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.get("/api/courses/{course_id}")
def get_course(course_id: int):
    db = get_db_session()
    try:
        c = db.query(Course).filter(Course.id == course_id).first()
        if not c:
            raise HTTPException(404, "课程不存在")
        return {**_course_dict(c),
                "materials": [{"id": m.id, "filename": m.filename, "type": m.file_type, "role": m.file_type, "weight": m.weight or 3,
                               "exists": Path(m.file_path).exists(),
                               "size_kb": round(Path(m.file_path).stat().st_size / 1024) if Path(m.file_path).exists() else 0}
                              for m in c.materials]}
    finally:
        db.close()


def _selected_materials(course_id: int, ids: list[int] | None) -> list[Material]:
    db = get_db_session()
    try:
        q = db.query(Material).filter(Material.course_id == course_id)
        if ids:
            q = q.filter(Material.id.in_(ids))
        return list(q.all())
    finally:
        db.close()



def _parse_material_cached(m, on_parse):
    """同一文件只解析一次；mtime/size/解析器版本变化才重新解析。"""
    try:
        st = os.stat(m.file_path)
        key = hashlib.md5(
            f"{PARSER_VERSION}|{m.file_path}|{st.st_mtime}|{st.st_size}".encode()).hexdigest()
    except OSError:
        return extract_text_from_file(m.file_path, on_progress=on_parse)
    cache_dir = paths.data_dir() / "parse_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{key}.json"
    if cache_file.is_file():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    pages = extract_text_from_file(m.file_path, on_progress=on_parse)
    try:
        cache_file.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return pages


def _run_job(job: Job, course: dict, task: str, options: dict) -> None:
    try:
        materials = _selected_materials(course["id"], options.get("material_ids"))
        material_notes = options.get("material_notes") or {}
        if not materials:
            raise RuntimeError("没有可用的资料")
        materials.sort(key=lambda m: (0 if (m.file_type or "core") == "core" else 1, -(m.weight or 3)))

        pages: list[str] = []
        for i, m in enumerate(materials):
            if job.stop.is_set():
                raise RuntimeError("已取消")
            def on_parse(done, total, stage="caption", _i=i, _n=len(materials)):
                frac = (done / max(1, total)) if total else 0
                job.emit(ProgressEvent(f"正在解析 {m.filename}（{done}/{total}）",
                                       0.02 + 0.06 * (_i + frac) / _n))
            body = _parse_material_cached(m, on_parse)
            tag = "重点资料" if (m.file_type or "core") == "core" else "辅助资料"
            _note = material_notes.get(str(m.id)) or material_notes.get(m.id) or ""
            _head = f"【{tag}·权重{m.weight or 3}" + (f"·老师说明：{_note}" if _note else "") + f"：{m.filename}】"
            pages.extend(_head + "\n" + p for p in body)

        # 任务级约束：每个任务独立读取，不跨模块复用
        constraints = TaskConstraints.from_options(task, options)
        if task != "guide" and constraints.has_scope:
            before = len(pages)
            pages = scope_pages(pages, constraints)
            text = "\n\n".join(pages)
            logger.info("任务范围 {}：{} 页 → {} 页", constraints.scope_label(), before, len(pages))
            if not pages:
                raise RuntimeError(f"所选页码范围（{constraints.scope_label()}）内没有解析到任何内容")
        text = "\n\n".join(pages)
        if task == "parse":
            job.status = "done"
            job.progress = 1.0
            job.message = "解析完成"
            job.result = {"pages": len(pages), "chars": len(text),
                          "images": text.count("[[[IMAGE:")}
            return
        if not text.strip():
            raise RuntimeError("资料没有解析出文字（可能是扫描件或空文件）")

        def _heartbeat():
            import time as _time
            started = _time.time()
            last = job.progress
            still = 0
            while job.status == "running":
                _time.sleep(2)
                if job.status != "running":
                    return
                if abs(job.progress - last) < 0.001:
                    still += 2
                else:
                    last = job.progress
                    still = 0
                if still >= 4 and job.progress < 0.9:
                    job.progress = min(0.9, job.progress + 0.006)
                    job.message = f"模型生成中…（已用 {int(_time.time() - started)} 秒）"

        threading.Thread(target=_heartbeat, daemon=True).start()

        if task == "chapter":
            import datetime
            import types
            from core.ai_engine import generate_super_guide
            from core.exporter import export_to_html
            from core.quality.dedupe import dedupe_markdown
            from services.guide_service import build_course_info

            db = get_db_session()
            try:
                gens = sorted(db.query(GeneratedFile)
                              .filter(GeneratedFile.course_id == course["id"]).all(),
                              key=lambda g: g.id, reverse=True)
                gen = None
                for g in gens:
                    if Path(g.file_path).with_suffix(".md").is_file():
                        gen = g
                        break
            finally:
                db.close()
            if not gen:
                raise RuntimeError("这门课还没有可编辑的讲义，请先生成一份")

            md_path = Path(gen.file_path).with_suffix(".md")
            md = md_path.read_text(encoding="utf-8")
            matches = list(re.finditer(r"(?m)^##\s*核心考点[:：].*?(?=^##\s*核心考点[:：]|\Z)", md, re.S))
            if not matches:
                raise RuntimeError("没有找到章节结构")
            idx = int(options.get("chapter_index", 0))
            if idx < 0 or idx >= len(matches):
                raise RuntimeError("章节序号超出范围")
            title = re.sub(r"^##\s*核心考点[:：]\s*", "",
                           matches[idx].group(0).splitlines()[0]).strip()

            job.emit(ProgressEvent(f"正在重写：{title}", 0.25))
            info = build_course_info(course)
            persona = options.get("persona") or course.get("persona", "温柔小姐姐")
            mode = options.get("mode", "key")
            new_chapter = generate_super_guide(
                text, info, persona=persona,
                user_choice="option_1_保命流" if mode == "key" else "option_2_完整流",
                lang=options.get("lang", "中文"),
                chapter={"title": title, "index": idx, "total": len(matches),
                         "must_know": [], "neighbors": ""},
                user_note=options.get("user_note", ""))
            if not new_chapter.strip():
                raise RuntimeError("模型没有返回内容，请重试")

            job.emit(ProgressEvent("正在重新排版…", 0.85))
            m = matches[idx]
            merged = dedupe_markdown(md[:m.start()] + new_chapter.strip() + "\n\n" + md[m.end():])

            paths.outputs_dir().mkdir(parents=True, exist_ok=True)
            out_path = paths.outputs_dir() / (
                f"{course['name']}_第{idx + 1}章重生成_{datetime.datetime.now():%m%d_%H%M}.html")
            ns = types.SimpleNamespace(name=course["name"], target_score=course["target_score"],
                                       days_left=course["days_left"])
            export_to_html(merged, str(out_path), course=ns, persona=persona,
                           doc_type="精简讲义" if mode == "key" else "全套讲义")
            out_path.with_suffix(".md").write_text(merged, encoding="utf-8")

            db = get_db_session()
            try:
                db.add(GeneratedFile(course_id=course["id"], file_path=str(out_path),
                                     created_at=datetime.datetime.now().strftime("%m%d_%H%M"),
                                     file_type="guide"))
                db.commit()
            finally:
                db.close()

            job.status = "done"
            job.progress = 1.0
            job.message = "重写完成"
            job.result = {"output_path": str(out_path),
                          "metrics": {"chars": len(merged), "chapter": title},
                          "quality": audit_markdown(merged, source_tags=text.count("[[[IMAGE:"))}
            return

        job.emit(ProgressEvent("正在生成…", 0.12))
        if task == "guide":
            result = guide_service.run_guide(
                course, mode=options.get("mode", "full"),
                persona=options.get("persona") or course.get("persona", "温柔小姐姐"),
                core_ratio=float(options.get("core_ratio", 0.8)),
                lang=options.get("lang", "中文"),
                user_note=options.get("user_note", ""),
                material_notes=material_notes,
                study_mode=options.get("material_mode", "exam"),
                material_ids=options.get("material_ids") or None,
                max_pages=(int(options["page_limit"]) if options.get("page_limit") else None),
                constraints=constraints,
                on_progress=job.emit, stop_event=job.stop)
        else:
            result = review_service.run_review(
                course, task, text,
                extract_type=options.get("extract_type"),
                with_answer=bool(options.get("with_answer", True)),
                mode=options.get("mode", "bundle"),
                train_type=options.get("train_type"),
                num_sets=int(options.get("num_sets", 1)),
                difficulty=max(2, min(4, (lambda base: base + {
                    "985": 1, "211": 1, "一本": 0, "二本": -1, "专科": -1}.get(course.get("school", "一本"), 0))(
                    (round((int(options.get("difficulty", 3)) + int(course.get("difficulty", 3))) / 2)
                     if int(options.get("difficulty", 3)) == 3 else int(options.get("difficulty", 3)))))),
                diy_config=options.get("diy_config", ""),
                user_context={"target_score": course["target_score"]},
                lang=options.get("lang", "中文"),
                user_note=options.get("user_note", ""),
                sections=options.get("sections") or None,
                reference_exam=bool(options.get("reference_exam")),
                material_mode=options.get("material_mode", "exam"),
                constraints=constraints,
                on_progress=job.emit, stop_event=job.stop)

        if result is None:
            job.status = "cancelled"
            job.message = "已取消"
            return
        try:
            md_text = getattr(result, "markdown", "") or ""
            if md_text and result.output_path:
                Path(result.output_path).with_suffix(".md").write_text(md_text, encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        job.status = "done"
        job.progress = 1.0
        job.message = "完成"
        md_text = getattr(result, "markdown", "") or ""
        result_metrics = getattr(result, "metrics", {}) or {}
        job.result = {"output_path": str(result.output_path),
                      "metrics": result_metrics,
                      "validation": result_metrics.get("validation"),
                      "warnings": getattr(result, "warnings", []) or [],
                      "quality": audit_markdown(md_text, source_tags=((result_metrics.get("images_source") or text.count("[[[IMAGE:")) if task == "guide" else 0),
                                                       require_headings=(task == "guide"),
                                                       source_text=text)
                      if md_text else None}
        try:
            db = get_db_session()
            latest = (db.query(GeneratedFile)
                      .filter(GeneratedFile.course_id == course["id"])
                      .order_by(GeneratedFile.id.desc()).first())
            if latest:
                latest.materials_used = len(materials)
                db.commit()
        except Exception:
            pass
        finally:
            try: db.close()
            except Exception: pass
        if md_text and not job.result["quality"]["passed"]:
            job.message = "完成（自检有问题）"
        validation = job.result.get("validation") or {}
        if validation and not validation.get("ok", True):
            # 非严格模式：结果照常交付，但必须让用户看见没过的硬校验
            job.message = "完成（硬校验未通过）"
        guide_metrics = getattr(result, "metrics", {}) or {}
        if task == "guide" and options.get("strict") and not guide_metrics.get("overview_mode"):
            cov = (guide_metrics.get("coverage") or {}).get("coverage", 1.0)
            issues = list(job.result["quality"].get("issues") or [])
            if cov < 0.8:
                issues.append(f"页覆盖率 {round(cov * 100)}% 低于 80%")
            if issues:
                job.status = "error"
                job.error = "严格模式未通过：" + "；".join(issues[:4])
                job.message = "严格校验未通过"
                return
        if task == "guide" and options.get("persona"):
            db = get_db_session()
            try:
                c = db.query(Course).filter(Course.id == course["id"]).first()
                if c:
                    c.persona = options["persona"]
                    db.commit()
            finally:
                db.close()
    except Exception as exc:  # noqa: BLE001
        if job.stop.is_set():
            job.status = "cancelled"
            job.message = "已取消"
        elif isinstance(exc, ConstraintViolation):
            job.status = "error"
            job.error = str(exc)
            job.message = "未通过生成后硬校验"
            job.result = {"validation": exc.to_dict()}
        else:
            job.status = "error"
            job.error = f"{type(exc).__name__}: {exc}"
            job.message = "失败"


@app.post("/api/jobs")
def create_job(payload: dict):
    course_id = int(payload.get("course_id") or 0)
    task = payload.get("task") or "guide"
    if task not in {"guide", "analysis", "extract", "exam", "parse", "chapter"}:
        raise HTTPException(400, "未知任务类型")
    if task in {"guide", "analysis", "extract", "exam", "chapter"}:
        from core import config as _cfg
        _k = (_cfg.get_key("DEEPSEEK_API_KEY", "") or "").strip()
        if not _k or _k == "sk-not-configured":
            raise HTTPException(400, "还没有填入 DeepSeek API Key，请先到「设置」里填写并测试连接。")
    db = get_db_session()
    try:
        c = db.query(Course).filter(Course.id == course_id).first()
        if not c:
            raise HTTPException(404, "课程不存在")
        course = _course_dict(c)
    finally:
        db.close()

    job = Job(task)
    with JOBS_LOCK:
        JOBS[job.id] = job
    threading.Thread(target=_run_job, args=(job, course, task, payload.get("options") or {}),
                     daemon=True).start()
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    return job.snapshot()


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    job.stop.set()
    if job.status == "running":
        job.status = "cancelled"
        job.message = "已取消"
    return {"ok": True}


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")

    async def stream():
        sent = 0
        while True:
            with JOBS_LOCK:
                batch = job.events[sent:]
                sent += len(batch)
            for e in batch:
                yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"
            if job.status != "running":
                yield "event: done\ndata: " + json.dumps(job.snapshot(), ensure_ascii=False) + "\n\n"
                return
            await asyncio.sleep(0.35)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/ask")
async def ask(payload: dict):
    from core.local_bridge import _answer
    return {"answer": await asyncio.to_thread(_answer, payload)}


@app.get("/api/notes")
def list_notes(course_id: int | None = None):
    db = get_db_session()
    try:
        q = db.query(Note, Course).join(Course, Note.course_id == Course.id)
        if course_id:
            q = q.filter(Note.course_id == course_id)
        rows = q.order_by(Note.id.desc()).limit(200).all()
        return [{"id": n.id, "course": c.name, "course_id": c.id, "chapter": n.chapter or "",
                 "question": n.question or "", "answer": n.answer or "",
                 "created_at": n.created_at or ""} for n, c in rows]
    finally:
        db.close()


@app.post("/api/notes")
def add_note(payload: dict):
    db = get_db_session()
    try:
        cid = int(payload.get("course_id") or 0)
        if not db.query(Course).filter(Course.id == cid).first():
            raise HTTPException(404, "课程不存在")
        import datetime
        note = Note(course_id=cid, chapter=(payload.get("chapter") or "")[:200],
                    question=(payload.get("question") or "")[:2000],
                    answer=(payload.get("answer") or "")[:8000],
                    created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        db.add(note)
        db.commit()
        return {"id": note.id}
    finally:
        db.close()


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int):
    db = get_db_session()
    try:
        n = db.query(Note).filter(Note.id == note_id).first()
        if not n:
            raise HTTPException(404, "笔记不存在")
        db.delete(n)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.get("/api/courses/{course_id}/classify")
def classify_course(course_id: int):
    from core.material_kind import classify_text
    db = get_db_session()
    try:
        c = db.query(Course).filter(Course.id == course_id).first()
        if not c:
            raise HTTPException(404, "课程不存在")
        mats = c.materials
    finally:
        db.close()
    if not mats:
        return {"kind": "unknown", "confidence": 0.0, "reasons": ["还没有资料"]}
    m = mats[0]
    pages = []
    try:
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FTimeout
        _ex = ThreadPoolExecutor(max_workers=1)
        _fut = _ex.submit(_parse_material_cached, m, None)
        try:
            pages = _fut.result(timeout=10)
        except _FTimeout:
            _fut.cancel()
            pages = []
        _ex.shutdown(wait=False)
    except Exception:
        pages = []
    text = "\n".join(pages)[:6000]
    return classify_text(text, " ".join(x.filename for x in mats))


@app.post("/api/open-browser")
def open_browser(payload: dict):
    browser = _find_browser()
    if not browser:
        raise HTTPException(501, "没有找到 Edge/Chrome")
    port = int(os.getenv("TERMFINALE_WEB_PORT", "8900"))
    page = payload.get("page") or "dashboard.html"
    course = payload.get("course")
    url = f"http://127.0.0.1:{port}/{page}"
    if course:
        url += f"?course={int(course)}"
    subprocess.Popen([browser, "--app=" + url, "--new-window"])
    return {"ok": True}


@app.get("/api/materials/all")
def all_materials(include_test: bool = False):
    db = get_db_session()
    try:
        q = db.query(Material, Course).join(Course, Material.course_id == Course.id)
        if not include_test:
            q = q.filter(_not_test_filter())
        rows = q.all()
        out = []
        for m, c in rows:
            try:
                size = round(os.path.getsize(m.file_path) / 1024) if os.path.exists(m.file_path) else 0
            except OSError:
                size = 0
            out.append({"id": m.id, "course_id": c.id, "course": c.name,
                        "filename": m.filename, "role": m.file_type or "core",
                        "weight": m.weight or 3, "size_kb": size,
                        "exists": os.path.exists(m.file_path)})
        return out
    finally:
        db.close()


@app.get("/api/mistakes")
def list_mistakes(course_id: int | None = None, include_test: bool = False):
    import datetime
    today = datetime.date.today().isoformat()
    db = get_db_session()
    try:
        q = db.query(Mistake, Course).join(Course, Mistake.course_id == Course.id)
        if course_id:
            q = q.filter(Mistake.course_id == course_id)
        if not include_test:
            q = q.filter(_not_test_filter())
        rows = q.order_by(Mistake.id.desc()).limit(300).all()
        out = []
        for m, c in rows:
            out.append({"id": m.id, "course": c.name, "course_id": c.id,
                        "question": m.question or "", "answer": m.answer or "",
                        "note": m.note or "", "stage": m.stage or 0,
                        "mastered": bool(m.mastered), "created_at": m.created_at or "",
                        "due_at": m.due_at or "", "due": (m.due_at or today) <= today and not m.mastered})
        return out
    finally:
        db.close()


@app.post("/api/mistakes")
def add_mistake(payload: dict):
    import datetime
    db = get_db_session()
    try:
        cid = int(payload.get("course_id") or 0)
        if not db.query(Course).filter(Course.id == cid).first():
            raise HTTPException(404, "课程不存在")
        today = datetime.date.today()
        m = Mistake(course_id=cid,
                    question=(payload.get("question") or "")[:3000],
                    answer=(payload.get("answer") or "")[:3000],
                    note=(payload.get("note") or "")[:1000],
                    stage=0, mastered=False,
                    created_at=today.isoformat(),
                    due_at=(today + datetime.timedelta(days=1)).isoformat())
        db.add(m); db.commit()
        return {"id": m.id}
    finally:
        db.close()


@app.post("/api/mistakes/{mistake_id}/review")
def review_mistake(mistake_id: int, payload: dict):
    import datetime
    intervals = [1, 2, 4, 7, 15, 30]
    db = get_db_session()
    try:
        m = db.query(Mistake).filter(Mistake.id == mistake_id).first()
        if not m:
            raise HTTPException(404, "错题不存在")
        today = datetime.date.today()
        if payload.get("known"):
            m.stage = min(len(intervals) - 1, (m.stage or 0) + 1)
        else:
            m.stage = 0
        m.mastered = (m.stage or 0) >= len(intervals) - 1
        m.due_at = (today + datetime.timedelta(days=intervals[m.stage or 0])).isoformat()
        db.commit()
        return {"stage": m.stage, "due_at": m.due_at, "mastered": m.mastered}
    finally:
        db.close()


@app.delete("/api/mistakes/{mistake_id}")
def delete_mistake(mistake_id: int):
    db = get_db_session()
    try:
        m = db.query(Mistake).filter(Mistake.id == mistake_id).first()
        if not m:
            raise HTTPException(404, "错题不存在")
        db.delete(m); db.commit()
        return {"ok": True}
    finally:
        db.close()


def _parse_quiz(md: str) -> list[dict]:
    """从试卷 Markdown 里解析选择题与答案。"""
    lines = md.splitlines()
    answers: dict[int, str] = {}
    for line in lines:
        m = re.match(r"\s*(\d{1,2})\s*[.、．]\s*(?:答案\s*[:：]\s*)?(?:\*\*)?([A-Da-d])(?:\*\*)?\b", line)
        if m:
            answers[int(m.group(1))] = m.group(2).upper()

    start = None
    for i, line in enumerate(lines):
        if re.match(r"^#{2,3}\s*.*选择", line):
            start = i
            break
    if start is None:
        return []
    questions: list[dict] = []
    cur = None
    for line in lines[start + 1:]:
        if re.match(r"^#{2,3}\s", line):
            break
        qm = re.match(r"^\s*(?:\*\*)?(\d{1,2})\s*[.、．](?:\*\*)?\s*(.*)", line)
        if qm:
            if cur:
                questions.append(cur)
            cur = {"no": int(qm.group(1)), "stem": qm.group(2).strip(), "options": {}}
            continue
        if cur is None:
            continue
        om = re.match(r"^\s*([A-D])\s*[.、．)]\s*(.*)", line)
        if om:
            cur["options"][om.group(1)] = om.group(2).strip()
        elif line.strip() and not line.strip().startswith("【考点"):
            cur["stem"] += " " + line.strip()
    if cur:
        questions.append(cur)

    out = []
    for q in questions:
        ans = answers.get(q["no"], "")
        if len(q["options"]) >= 2 and ans in q["options"]:
            out.append({**q, "answer": ans})
    return out


@app.get("/api/exams/{file_id}/quiz")
def exam_quiz(file_id: int):
    db = get_db_session()
    try:
        gen = db.query(GeneratedFile).filter(GeneratedFile.id == file_id).first()
        if not gen:
            raise HTTPException(404, "试卷不存在")
        md_path = Path(gen.file_path).with_suffix(".md")
        if not md_path.is_file():
            return {"exists": False, "reason": "旧试卷没有 Markdown 源，请重新生成"}
        questions = _parse_quiz(md_path.read_text(encoding="utf-8"))
        return {"exists": True, "filename": Path(gen.file_path).name, "questions": questions}
    finally:
        db.close()


@app.get("/api/practice")
def practice_data(include_test: bool = False):
    db = get_db_session()
    try:
        q = (db.query(GeneratedFile, Course)
             .join(Course, GeneratedFile.course_id == Course.id)
             .filter(GeneratedFile.file_type.in_(["exam", "训练试卷"])))
        if not include_test:
            q = q.filter(_not_test_filter())
        rows = q.order_by(GeneratedFile.id.desc()).limit(20).all()
        exams = [{"id": g.id, "course": c.name, "course_id": c.id,
                  "filename": Path(g.file_path).name,
                  "has_md": Path(g.file_path).with_suffix(".md").is_file(),
                  "created_at": g.created_at or ""} for g, c in rows]
        note_count = db.query(Note).count()
        import datetime
        today = datetime.date.today().isoformat()
        mq = db.query(Mistake).join(Course, Mistake.course_id == Course.id).filter(Mistake.mastered == False)  # noqa: E712
        if not include_test:
            mq = mq.filter(_not_test_filter())
        mistakes = mq.all()
        due = sum(1 for m in mistakes if (m.due_at or today) <= today)
        return {"exams": exams, "notes": note_count,
                "mistakes": len(mistakes), "due": due}
    finally:
        db.close()


def _find_browser() -> str | None:
    candidates = []
    if sys.platform == "darwin":
        candidates = ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                      "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    elif os.name == "nt":
        for base in (os.getenv("PROGRAMFILES(X86)", ""), os.getenv("PROGRAMFILES", ""),
                     os.getenv("LOCALAPPDATA", "")):
            if base:
                candidates += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                               os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    else:
        for name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
            found = shutil.which(name)
            if found:
                candidates.append(found)
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return None


@app.get("/api/courses/{course_id}/pdf")
def export_course_pdf(course_id: int):
    db = get_db_session()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(404, "课程不存在")
        name = course.name
        # 直接打印已经生成的单文件 HTML；打印动态 reader 会抓到“正在加载”和脚本。
        latest = (db.query(GeneratedFile)
                  .filter(GeneratedFile.course_id == course_id)
                  .order_by(GeneratedFile.id.desc()).first())
        html_path = Path(latest.file_path) if latest and latest.file_path else None
    finally:
        db.close()

    browser = _find_browser()
    if not browser:
        raise HTTPException(501, "没有找到 Edge/Chrome，暂时只能用打印对话框导出 PDF")

    import datetime
    paths.outputs_dir().mkdir(parents=True, exist_ok=True)
    out = paths.outputs_dir() / f"{name}_讲义_{datetime.datetime.now():%m%d_%H%M%S}.pdf"
    port = int(os.getenv("TERMFINALE_WEB_PORT", "8900"))
    if html_path and html_path.is_file():
        url = html_path.as_uri()
    else:
        url = f"http://127.0.0.1:{port}/reader.html?course={course_id}"
    try:
        subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        "--virtual-time-budget=8000", f"--print-to-pdf={out}", url],
                       timeout=120, capture_output=True)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "PDF 生成超时，请重试")
    if not out.is_file() or out.stat().st_size < 1024:
        raise HTTPException(500, "PDF 生成失败，请改用打印对话框")
    return FileResponse(out, media_type="application/pdf", filename=out.name)


@app.get("/api/settings")
def settings_info():
    from core import maintenance
    from core.build_info import BUILD_TIME, VERSION
    return {
        "keys": key_status(),
        "models": {"text": config.text_model(), "vision": config.vision_model(),
                   "ocr": os.getenv("TERMFINALE_OCR_MODEL", "qwen-vl-ocr"),
                   "asr": os.getenv("TERMFINALE_ASR_MODEL", "qwen3-asr-flash")},
        "paths": {"data": str(paths.data_dir()), "env": str(config.user_env_path()),
                  "outputs": str(paths.outputs_dir()), "assets": str(paths.assets_dir())},
        "cache": maintenance.cache_report(),
        "version": VERSION, "build_time": BUILD_TIME,
        "concurrency": os.getenv("TERMFINALE_CONCURRENCY", "2"),
    }


@app.post("/api/settings/prune")
def prune_cache(payload: dict | None = None):
    from core import maintenance
    keep = int((payload or {}).get("keep", 100))
    return maintenance.prune_debug(keep)


@app.post("/api/settings/test")
async def test_keys(payload: dict):
    from openai import OpenAI

    def check(api_key: str, base: str) -> str:
        try:
            OpenAI(api_key=api_key, base_url=base).models.list()
            return "ok"
        except Exception as exc:  # noqa: BLE001
            return f"{type(exc).__name__}: {exc}"

    out = {}
    if payload.get("deepseek") or config.get_key("DEEPSEEK_API_KEY"):
        key = (payload.get("deepseek") or "").strip() or config.get_key("DEEPSEEK_API_KEY")
        out["deepseek"] = await asyncio.to_thread(check, key, "https://api.deepseek.com")
    if payload.get("dashscope") or config.get_key("DASHSCOPE_API_KEY"):
        key = (payload.get("dashscope") or "").strip() or config.get_key("DASHSCOPE_API_KEY")
        out["dashscope"] = await asyncio.to_thread(
            check, key, "https://dashscope.aliyuncs.com/compatible-mode/v1")
    return out


@app.get("/api/profile")
def get_profile():
    db = get_db_session()
    try:
        p = db.query(Profile).order_by(Profile.id).first()
        if not p:
            return {"onboarded": False}
        return {"onboarded": bool(p.onboarded), "name": p.name or "", "identity": p.identity or "学生",
                "major": p.major or "", "avatar": p.avatar or ""}
    finally:
        db.close()


@app.post("/api/profile")
def save_profile(payload: dict):
    import datetime
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "名字不能为空")
    db = get_db_session()
    try:
        p = db.query(Profile).order_by(Profile.id).first()
        if not p:
            p = Profile(created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            db.add(p)
        p.name = name[:50]
        p.identity = (payload.get("identity") or "学生")[:50]
        if payload.get("major") is not None:
            p.major = (payload.get("major") or "")[:100]
        if payload.get("avatar") is not None:
            avatar = payload.get("avatar") or ""
            if len(avatar) > 400000:
                raise HTTPException(400, "头像文件过大，请换一张小图")
            p.avatar = avatar
        p.onboarded = True
        db.commit()
        return {"ok": True, "name": p.name}
    finally:
        db.close()


def _backup_db(prefix: str = "manual") -> Path:
    """用 sqlite backup API 落一份可独立打开的备份（WAL 也会合并进去）。"""
    import sqlite3
    backup_dir = paths.data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.db"
    src = sqlite3.connect(str(paths.db_path()))
    try:
        dst = sqlite3.connect(str(target))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return target


def _is_under(path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


@app.post("/api/backup")
def create_backup():
    target = _backup_db("manual")
    return {"ok": True, "path": str(target),
            "size_kb": round(target.stat().st_size / 1024, 1)}


@app.get("/api/backups")
def list_backups():
    backup_dir = paths.data_dir() / "backups"
    items = []
    if backup_dir.is_dir():
        for p in sorted(backup_dir.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            items.append({"name": p.name, "path": str(p),
                          "size_kb": round(p.stat().st_size / 1024, 1),
                          "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime))})
    return items


@app.post("/api/reset")
def reset_all_data(payload: dict | None = None):
    if (payload or {}).get("confirm") != "DELETE-ALL":
        raise HTTPException(400, "需要 confirm=DELETE-ALL 才允许清空")
    backup = _backup_db("pre_reset")
    uploads = paths.data_dir() / "uploads"
    db = get_db_session()
    try:
        kept_external = 0
        for g in db.query(GeneratedFile).all():
            for q in (Path(g.file_path), Path(g.file_path).with_suffix(".md"),
                      Path(g.file_path).with_suffix(".pdf")):
                try:
                    if q.is_file():
                        q.unlink()
                except OSError:
                    pass
        for m in db.query(Material).all():
            # 只删我们托管的上传副本；用户桌面/Documents 里的原资料绝不删
            if not _is_under(m.file_path, uploads):
                kept_external += 1
                continue
            try:
                p = Path(m.file_path)
                if p.is_file():
                    p.unlink()
            except OSError:
                pass
        db.query(Mistake).delete(); db.query(Note).delete()
        db.query(GeneratedFile).delete(); db.query(Material).delete()
        db.query(Course).delete(); db.query(Profile).delete()
        db.commit()
        return {"ok": True, "backup": str(backup), "kept_external_materials": kept_external}
    finally:
        db.close()


@app.get("/api/settings/keys")
def key_status():
    def mask(name: str):
        v = config.get_key(name)
        return {"configured": bool(v), "tail": v[-4:] if v else ""}
    return {"deepseek": mask("DEEPSEEK_API_KEY"), "dashscope": mask("DASHSCOPE_API_KEY"),
            "env_file": str(config.user_env_path())}


@app.post("/api/settings/keys")
def save_keys(payload: dict):
    for name, field in (("DEEPSEEK_API_KEY", "deepseek"), ("DASHSCOPE_API_KEY", "dashscope")):
        value = (payload.get(field) or "").strip()
        if value:
            config.save_key(name, value)
    return {"ok": True}


@app.get("/api/jobs/{job_id}/file")
def job_file(job_id: str):
    job = JOBS.get(job_id)
    if not job or not job.result or not job.result.get("output_path"):
        raise HTTPException(404, "结果不存在")
    target = Path(job.result["output_path"])
    if not target.is_file():
        raise HTTPException(404, "文件已被移动或删除")
    return FileResponse(target, media_type="text/html", filename=target.name)


def _file_view(c, f):
    path = Path(f.file_path)
    md_path = path.with_suffix(".md")
    if not md_path.is_file():
        return {"exists": False, "reason": "旧文件没有 Markdown 源，请重新生成", "course": _course_dict(c)}
    html, toc = _render_markdown(md_path.read_text(encoding="utf-8"))
    import datetime
    generated_at = datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%m-%d %H:%M")
    return {"exists": True, "course": _course_dict(c), "html": html, "toc": toc,
            "filename": path.name, "type": f.file_type, "file_id": f.id,
            "materials": len(c.materials),
            "materials_used": getattr(f, "materials_used", 0) or len(c.materials),
            "generated_at": generated_at}


@app.get("/api/courses/{course_id}/files")
def course_files(course_id: int):
    db = get_db_session()
    try:
        c = db.query(Course).filter(Course.id == course_id).first()
        if not c:
            raise HTTPException(404, "课程不存在")
        out = []
        import json as _json
        for f in sorted(c.generated_files, key=lambda x: x.id, reverse=True):
            p = Path(f.file_path)
            try:
                _m = _json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
            except Exception:
                _m = {}
            out.append({"id": f.id, "type": f.file_type, "filename": p.name, "meta": _m,
                        "created_at": p.stat().st_mtime if p.exists() else 0,
                        "materials_used": getattr(f, "materials_used", 0) or len(c.materials),
                        "size_kb": round(p.stat().st_size / 1024) if p.exists() else 0,
                        "exists": p.exists()})
        return {"course": _course_dict(c), "files": out}
    finally:
        db.close()


@app.get("/api/files/{file_id}/view")
def file_view(file_id: int):
    db = get_db_session()
    try:
        f = db.query(GeneratedFile).filter(GeneratedFile.id == file_id).first()
        if not f:
            raise HTTPException(404, "文件不存在")
        c = db.query(Course).filter(Course.id == f.course_id).first()
        return _file_view(c, f)
    finally:
        db.close()


@app.get("/api/courses/{course_id}/latest")
def latest_content(course_id: int):
    db = get_db_session()
    try:
        c = db.query(Course).filter(Course.id == course_id).first()
        if not c:
            raise HTTPException(404, "课程不存在")
        files = sorted(c.generated_files, key=lambda f: f.id, reverse=True)
        if not files:
            return {"exists": False, "course": _course_dict(c)}
        return _file_view(c, files[0])
    finally:
        db.close()


@app.get("/api/assets/{name}")
def asset(name: str):
    target = paths.assets_dir() / Path(name).name
    if not target.is_file():
        raise HTTPException(404, "资源不存在")
    return FileResponse(target)


@app.get("/api/courses/{course_id}/preview")
def preview(course_id: int):
    """最近一次生成的 HTML 路径（给阅读器/预览用）。"""
    db = get_db_session()
    try:
        c = db.query(Course).filter(Course.id == course_id).first()
        if not c:
            raise HTTPException(404, "课程不存在")
        files = sorted([f for f in c.generated_files], key=lambda f: f.id, reverse=True)
        if not files:
            return {"exists": False}
        f = files[0]
        return {"exists": Path(f.file_path).exists(), "path": f.file_path,
                "filename": Path(f.file_path).name, "type": f.file_type}
    finally:
        db.close()


def _page(name: str) -> FileResponse:
    target = WEB / name
    if not target.is_file():
        raise HTTPException(404, "页面不存在")
    return FileResponse(target)


@app.get("/")
@app.get("/review_plan.html")
def review_plan_page():
    return _page("review_plan.html")


@app.get("/materials_stats.html")
def materials_stats_page():
    return _page("materials_stats.html")


@app.get("/welcome.html")
def welcome_page():
    return _page("welcome.html")


@app.get("/dashboard.html")
def dashboard():
    return _page("dashboard.html")


@app.get("/practice.html")
def practice_page():
    return _page("practice.html")


@app.get("/notes.html")
def notes_page():
    return _page("notes.html")


@app.get("/settings.html")
def settings_page():
    return _page("settings.html")


@app.get("/upload.html")
def upload_page():
    return _page("upload.html")


@app.get("/generate.html")
def generate_page():
    return _page("generate.html")


@app.get("/courses.html")
def courses_page():
    return _page("courses.html")


@app.get("/course_detail.html")
def course_detail_page():
    return _page("course_detail.html")


@app.get("/course_files.html")
def course_files_page():
    return _page("course_files.html")


@app.get("/reader.html")
def reader_page():
    return _page("reader.html")


app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")


def main() -> None:
    import uvicorn
    config.load_env()
    paths.ensure_dirs()
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("TERMFINALE_WEB_PORT", "8900")),
                log_level="warning")


if __name__ == "__main__":
    main()
