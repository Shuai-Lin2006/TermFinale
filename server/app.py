"""TermFinale 本地 API：给新 Web UI 提供课程、生成任务、问答与设置。

启动：python server/app.py    （默认 127.0.0.1:8900）
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))

from core import config, paths  # noqa: E402
from core.database import Course, GeneratedFile, Material, get_db_session  # noqa: E402
from core.parser import extract_text_from_file  # noqa: E402
from services import guide_service, review_service  # noqa: E402
from services.task import ProgressEvent  # noqa: E402

WEB = ROOT / "web"
app = FastAPI(title="TermFinale API", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
                "result": self.result, "error": self.error}


def _course_dict(course: Course) -> dict:
    return {"id": course.id, "name": course.name, "major": course.major,
            "school": course.school_level, "credits": course.credits,
            "days_left": course.days_left, "target_score": course.target_score,
            "difficulty": course.user_difficulty, "is_major": course.is_major,
            "persona": course.persona or "温柔小姐姐"}




import re as _re
import markdown as _markdown
from urllib.parse import quote as _quote


def _render_markdown(md: str) -> tuple[str, list[dict]]:
    """把讲义 Markdown 转成阅读器 HTML（数学公式保留给 KaTeX 客户端渲染）。"""
    md = _re.sub(r"\[\[\[IMAGE:\s*([^|\]]+?)\s*\|\s*图注:\s*(.*?)\]\]\]",
                 lambda m: f'\n\n<figure class="figure"><img src="/api/assets/{_quote(m.group(1).strip())}"'
                           f' alt="{m.group(2).strip()}"><figcaption>{m.group(2).strip()}</figcaption></figure>\n\n',
                 md)
    md = _re.sub(r"\[\[([^|\]]+?)\|([^\]]+?)\]\]",
                 lambda m: f'<span class="kw" title="{m.group(2).strip()}">{m.group(1).strip()}</span>', md)

    math: list[str] = []
    def stash(m):
        math.append(m.group(0))
        return f"@@MATH{len(math) - 1}@@"
    md = _re.sub(r"(\$\$.*?\$\$|\$[^$\n]+?\$)", stash, md, flags=_re.S)
    html = _markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    for i, tex in enumerate(math):
        html = html.replace(f"@@MATH{i}@@", tex)

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
            m2 = _re.match(r"\s*核心考点[:：]\s*(.*)", text)
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

@app.get("/api/health")
def health():
    return {"ok": True, "time": time.strftime("%Y-%m-%d %H:%M")}


@app.get("/api/courses")
def list_courses():
    db = get_db_session()
    try:
        out = []
        for c in db.query(Course).order_by(Course.days_left.asc()).all():
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
def overview():
    courses = list_courses()
    db = get_db_session()
    try:
        rows = (db.query(GeneratedFile, Course)
                .join(Course, GeneratedFile.course_id == Course.id)
                .order_by(GeneratedFile.id.desc()).limit(6).all())
        recent = []
        for gen, course in rows:
            path = Path(gen.file_path)
            recent.append({"course": course.name, "course_id": course.id,
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


@app.get("/api/courses/{course_id}")
def get_course(course_id: int):
    db = get_db_session()
    try:
        c = db.query(Course).filter(Course.id == course_id).first()
        if not c:
            raise HTTPException(404, "课程不存在")
        return {**_course_dict(c),
                "materials": [{"id": m.id, "filename": m.filename, "type": m.file_type,
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


def _run_job(job: Job, course: dict, task: str, options: dict) -> None:
    try:
        materials = _selected_materials(course["id"], options.get("material_ids"))
        if not materials:
            raise RuntimeError("没有可用的资料")

        pages: list[str] = []
        for i, m in enumerate(materials):
            if job.stop.is_set():
                raise RuntimeError("已取消")
            def on_parse(done, total, stage="caption", _i=i, _n=len(materials)):
                frac = (done / max(1, total)) if total else 0
                job.emit(ProgressEvent(f"正在解析 {m.filename}（{done}/{total}）",
                                       0.02 + 0.06 * (_i + frac) / _n))
            pages.extend(extract_text_from_file(m.file_path, on_progress=on_parse))
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

        job.emit(ProgressEvent("正在生成…", 0.12))
        if task == "guide":
            result = guide_service.run_guide(
                course, mode=options.get("mode", "full"),
                persona=options.get("persona") or course.get("persona", "温柔小姐姐"),
                core_ratio=float(options.get("core_ratio", 0.8)),
                lang=options.get("lang", "中文"),
                user_note=options.get("user_note", ""),
                on_progress=job.emit, stop_event=job.stop)
        else:
            result = review_service.run_review(
                course, task, text,
                extract_type=options.get("extract_type"),
                with_answer=bool(options.get("with_answer", True)),
                mode=options.get("mode", "bundle"),
                train_type=options.get("train_type"),
                num_sets=int(options.get("num_sets", 1)),
                difficulty=int(options.get("difficulty", 3)),
                diy_config=options.get("diy_config", ""),
                user_context={"target_score": course["target_score"]},
                lang=options.get("lang", "中文"),
                user_note=options.get("user_note", ""),
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
        job.result = {"output_path": str(result.output_path),
                      "metrics": getattr(result, "metrics", {}) or {}}
    except Exception as exc:  # noqa: BLE001
        if job.stop.is_set():
            job.status = "cancelled"
            job.message = "已取消"
        else:
            job.status = "error"
            job.error = f"{type(exc).__name__}: {exc}"
            job.message = "失败"


@app.post("/api/jobs")
def create_job(payload: dict):
    course_id = int(payload.get("course_id") or 0)
    task = payload.get("task") or "guide"
    if task not in {"guide", "analysis", "extract", "exam", "parse"}:
        raise HTTPException(400, "未知任务类型")
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
        f = files[0]
        path = Path(f.file_path)
        md_path = path.with_suffix(".md")
        if not md_path.is_file():
            return {"exists": False, "reason": "旧文件没有 Markdown 源，请重新生成",
                    "course": _course_dict(c)}
        html, toc = _render_markdown(md_path.read_text(encoding="utf-8"))
        import datetime
        generated_at = datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%m-%d %H:%M")
        return {"exists": True, "course": _course_dict(c), "html": html, "toc": toc,
                "filename": path.name, "type": f.file_type,
                "materials": len(c.materials), "generated_at": generated_at}
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
@app.get("/dashboard.html")
def dashboard():
    return _page("dashboard.html")


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
