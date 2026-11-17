from pathlib import Path
p = Path("tfv2/api/product_app.py")
s = p.read_text()
a = s.index('@app.post("/api/artifacts/{aid}/generate-selected")')
b = s.index('@app.post("/api/artifacts/{aid}/review")')
new = '''@app.post("/api/artifacts/{aid}/generate-selected")
def artifact_generate_selected(aid: str, payload: SelectedPreviewPayload) -> dict:
    from tfv2.product import generate, service
    if not payload.pages:
        raise HTTPException(status_code=422, detail="至少选一页")
    pages = sorted({int(p) for p in payload.pages})
    if len(pages) > 8:
        raise HTTPException(status_code=422, detail="当前单次最多 8 页；全量分批后续开放")
    art = service.artifact_path(aid)
    if art is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    pdf = next((art / "source").glob("*.pdf"), None)
    if pdf is None:
        raise HTTPException(status_code=404, detail="source pdf not found")
    meta = service.get_artifact(aid) or {}
    course = service.get_course(str(meta.get("course_key") or ""))
    title = (course or {}).get("name") or meta.get("title") or "选中页讲义"
    job_id = uuid.uuid4().hex[:12]
    store.create_job(job_id, "selected_lecture", payload={"artifact_id": aid, "pages": pages})
    pdf_path = str(pdf)

    def run() -> None:
        try:
            import pymupdf
            src = pymupdf.open(pdf_path)
            out = pymupdf.open()
            try:
                for n in pages:
                    if 1 <= n <= len(src):
                        out.insert_pdf(src, from_page=n - 1, to_page=n - 1)
                if len(out) == 0:
                    raise ValueError("页码超出范围")
                work = generate.UPLOAD_ROOT / ("selected-" + job_id)
                work.mkdir(parents=True, exist_ok=True)
                target = work / "selected.pdf"
                out.save(str(target))
            finally:
                out.close(); src.close()
            def prog(pct: int, step: str) -> None:
                job = store.get_job(job_id)
                if job and job.get("status") == "cancelled":
                    raise generate.GenerateError("已取消")
                store.update_job(job_id, progress=max(0, min(100, int(pct))), step=step)
            result = generate.generate_lecture(
                target, title=title, course=title, target_score=80, days_left=7,
                foundation="基础较弱", persona="老师", custom_prompt="", gen_lang="zh",
                illustrations=False, progress=prog,
            )
            store.update_job(job_id, status="done", progress=100, step="完成",
                             result=json.dumps(result, ensure_ascii=False))
        except Exception as exc:
            store.update_job(job_id, status="failed", error=f"{type(exc).__name__}: {str(exc)[:300]}", step="失败")

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "pages": len(pages)}


'''
p.write_text(s[:a] + new + s[b:])
print("patched")
