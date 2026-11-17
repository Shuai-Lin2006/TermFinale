from pathlib import Path
p = Path("tfv2/product/preview_generate.py")
s = p.read_text()
s = s.replace("from tfv2.authoring.lecture import author_section", "from tfv2.authoring.lecture import author_section\nfrom tfv2.authoring.normalize import normalize_section")
s = s.replace("[:8]", "[:16]")
a = s.index("    texts = {i + 1:")
b = s.index("    dst = service.artifact_path(job_id)")
new = '''    sections = []
    client = DeepSeekClient(model="deepseek-flash")
    chunk_size = 4
    chunks = [rows[i:i + chunk_size] for i in range(0, len(rows), chunk_size)]
    for ci, chunk in enumerate(chunks, 1):
        offset = (ci - 1) * chunk_size
        local_texts = {j + 1: (row.get("text") or "") for j, row in enumerate(chunk)}
        local_ledger = PageLedger(
            material=artifact_id, page_count=len(chunk), source_hash="preview",
            parser_version="preview",
            pages=[Page(material=artifact_id, page_no=j, text=local_texts[j], quality=PageQuality.OCR)
                   for j in local_texts],
        )
        local_facts = facts_for_pages(local_texts, list(local_texts), per_page=8)
        if progress:
            progress(12 + int(46 * (ci - 1) / max(1, len(chunks))), f"第 {ci}/{len(chunks)} 单元：规划")
        sec = author_section(
            client, local_ledger, chapter_title="预览",
            section_title=f"第 {offset + 1}–{offset + len(chunk)} 页",
            pages=list(local_texts), target_score=80, days_left=7,
            foundation="基础较弱", persona="老师", gen_lang="zh",
            extra_note=f"这是预览，只写这 {len(chunk)} 页；不要扩展到其他页。", clamp_pages=True,
        )
        mapped = map_facts(local_facts, [sec])
        covered = {x.get("fact_id") or x.get("id") for x in mapped["facts"] if x.get("status") == "covered"}
        for f in local_facts:
            fid = f.get("fact_id") or f["id"]
            if fid not in covered:
                sec.blocks.append(LectureBlock(
                    id=f"fallback-{ci}-{fid}", kind=BlockKind.PARAGRAPH, text=f["text"],
                    source_refs=[SourceRef(material=artifact_id, page_start=f["page"], page_end=f["page"])]))
        sec.source_refs = [SourceRef(material=artifact_id, page_start=1, page_end=len(chunk))]
        sec = normalize_section(sec, list(range(1, len(chunk) + 1)))
        for block in sec.blocks:
            for ref in block.source_refs:
                ref.page_start = min(len(rows), ref.page_start + offset)
                ref.page_end = min(len(rows), ref.page_end + offset)
        for ref in sec.source_refs:
            ref.page_start = min(len(rows), ref.page_start + offset)
            ref.page_end = min(len(rows), ref.page_end + offset)
        sections.append(sec)
    if progress:
        progress(58, "正文生成 / 结构整理")

'''
s = s[:a] + new + s[b:]
s = s.replace('(dst / "sections.json").write_text(json.dumps([sec.model_dump(mode="json")], ensure_ascii=False, indent=2), encoding="utf-8")', '(dst / "sections.json").write_text(json.dumps([x.model_dump(mode="json") for x in sections], ensure_ascii=False, indent=2), encoding="utf-8")')
p.write_text(s)
print("patched")
