from pathlib import Path
p = Path("tfv2/api/product_app.py")
s = p.read_text()
a = s.index('@app.post("/api/artifacts/{aid}/generate-selected")')
b = s.index('@app.post("/api/artifacts/{aid}/review")')
new = '''@app.post("/api/artifacts/{aid}/generate-selected")
def artifact_generate_selected(aid: str, payload: SelectedPreviewPayload) -> dict:
    from tfv2.product import service
    from tfv2.product.preview_generate import generate_preview
    if not payload.pages:
        raise HTTPException(status_code=422, detail="至少选一页")
    pages = sorted({int(p) for p in payload.pages})
    if len(pages) > 2:
        raise HTTPException(status_code=422, detail="当前先支持 2 页生成；更多页需分批")
    if service.artifact_path(aid) is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    job_id = uuid.uuid4().hex[:12]
    store.create_job(job_id, "selected_lecture", payload={"artifact_id": aid, "pages": pages})

    def run() -> None:
        try:
            out = generate_preview(aid, job_id, page_numbers=pages)
            store.update_job(job_id, status="done", progress=100, step="完成",
                             result=json.dumps({"preview": True, "pdf_url": f"/api/previews/{job_id}.pdf",
                                                "pages": len(pages)}, ensure_ascii=False))
        except Exception as exc:
            store.update_job(job_id, status="failed", error=f"{type(exc).__name__}: {str(exc)[:300]}", step="失败")

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "pages": len(pages)}


'''
p.write_text(s[:a] + new + s[b:])
print("patched")
