from pathlib import Path
p = Path("tfv2/api/product_app.py")
s = p.read_text()
old = '''            out = generate_preview(
                aid, job_id, page_numbers=pages,
                progress=lambda pct, step: store.update_job(job_id, progress=int(pct), step=step),
            )
            store.update_job(job_id, status="done", progress=100, step="完成",
                             result=json.dumps({"preview": True, "pdf_url": f"/api/previews/{job_id}.pdf",
                                                "pages": len(pages)}, ensure_ascii=False))'''
new = '''            out = generate_preview(
                aid, job_id, page_numbers=pages,
                progress=lambda pct, step: store.update_job(job_id, progress=int(pct), step=step),
            )
            import shutil
            art_id = "sel-" + job_id
            dest = generate.ARTIFACT_ROOT / art_id
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(out.parent, dest)
            import pymupdf
            pdf_doc = pymupdf.open(str(dest / "lecture.pdf"))
            pdf_pages = len(pdf_doc)
            pdf_doc.close()
            sections = json.loads((dest / "sections.json").read_text(encoding="utf-8"))
            manifest = {
                "artifact": art_id, "chapter": title, "page_count": len(pages),
                "scope_pages": list(range(1, len(pages) + 1)), "sections": len(sections),
                "figures": 0, "pdf_pages": pdf_pages,
                "gate": {"passed": False, "issues": [{"message": "预览生成，未做逐页覆盖审计"}]},
                "language": {},
            }
            (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            store.update_job(job_id, status="done", progress=100, step="完成",
                             result=json.dumps({"preview": False, "artifact_id": art_id,
                                                "pdf_url": f"/artifact/{art_id}/lecture.pdf",
                                                "pages": len(pages)}, ensure_ascii=False))'''
if old not in s:
    raise SystemExit("block not found")
s = s.replace(old, new)
p.write_text(s)
print("patched")
