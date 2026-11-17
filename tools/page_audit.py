"""逐页结构排查：页账本、block 出处、语义审计状态、PDF、图源。

用法：
  PYTHONPATH=. .venv/bin/python tools/page_audit.py
输出：
  docs/evidence/v3_page_audit.md / .json
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence"


def audit_artifact(path: Path) -> dict:
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    page_count = int(manifest.get("page_count") or 0)
    scope_raw = manifest.get("scope_pages")
    scope: set[int]
    if isinstance(scope_raw, list):
        scope = {int(x) for x in scope_raw}
    elif isinstance(scope_raw, str) and "-" in scope_raw:
        a, b = scope_raw.split("-", 1)
        scope = set(range(int(a), int(b) + 1))
    else:
        scope = set(range(1, page_count + 1))
    sections = []
    sp = path / "sections.json"
    if sp.is_file():
        data = json.loads(sp.read_text(encoding="utf-8"))
        sections = data if isinstance(data, list) else []
    block_pages: set[int] = set()
    section_pages: set[int] = set()
    for sec in sections:
        for ref in sec.get("source_refs") or []:
            section_pages.update(range(int(ref["page_start"]), int(ref.get("page_end") or ref["page_start"]) + 1))
        for block in sec.get("blocks") or []:
            for ref in block.get("source_refs") or []:
                block_pages.update(range(int(ref["page_start"]), int(ref.get("page_end") or ref["page_start"]) + 1))
            fig = block.get("figure") or {}
            src = fig.get("source") or {}
            if src:
                block_pages.add(int(src.get("page_start") or 0))
    audit = []
    ap = path / "coverage_audit.json"
    if ap.is_file():
        audit = json.loads(ap.read_text(encoding="utf-8"))
    counts = Counter(x.get("status") for x in audit if isinstance(x, dict))
    audit_pages = {int(x.get("page_no")): x.get("status") for x in audit if isinstance(x, dict)}
    expected = {p for p in scope if 1 <= p <= page_count}
    has_sections = bool(sections)
    visual_pages = {int(x.get("page_no")) for x in audit if isinstance(x, dict) and x.get("status") == "visual"}
    missing_block = sorted(expected - block_pages - visual_pages) if has_sections else None
    missing_section = sorted(expected - section_pages - visual_pages) if has_sections else None
    missing_audit = sorted(expected - set(audit_pages)) if audit else sorted(expected)

    pdf_info = {"pages": None, "bookmarks": None, "links": None}
    pdf = path / "lecture.pdf"
    if pdf.is_file():
        import pymupdf
        doc = pymupdf.open(str(pdf))
        pdf_info = {
            "pages": len(doc),
            "bookmarks": len(doc.get_toc()),
            "links": sum(len(p.get_links()) for p in doc),
            "blank_pages": [i + 1 for i, page in enumerate(doc) if len(page.get_text().strip()) < 10],
            "images": sum(len(page.get_images()) for page in doc),
        }
        doc.close()

    figures = []
    fp = path / "figure_report.json"
    if fp.is_file():
        figures = json.loads(fp.read_text(encoding="utf-8"))
    fig_bad = [f for f in figures if f.get("status") not in ("ok", "ok_schematic")]
    missing_assets = [f.get("asset_path") for f in figures if not f.get("asset_exists")]
    return {
        "id": path.name,
        "title": manifest.get("chapter") or manifest.get("artifact") or path.name,
        "page_count": page_count,
        "sections": len(sections),
        "has_sections": has_sections,
        "scope": sorted(expected),
        "block_pages": len(block_pages & expected),
        "missing_block_pages": missing_block,
        "missing_section_pages": missing_section,
        "audit_present": bool(audit),
        "audit_counts": dict(counts),
        "missing_audit_pages": missing_audit,
        "partial_pages": [p for p, s in audit_pages.items() if s == "partial"],
        "missing_pages": [p for p, s in audit_pages.items() if s == "missing"],
        "visual_pages": [p for p, s in audit_pages.items() if s == "visual"],
        "pdf": pdf_info,
        "figures": len(figures),
        "figures_bad": fig_bad,
        "missing_assets": missing_assets,
    }


def main() -> None:
    items = []
    for path in sorted(EVIDENCE.glob("v2_*")):
        if (path / "manifest.json").is_file():
            try:
                items.append(audit_artifact(path))
            except Exception as exc:  # noqa: BLE001
                items.append({"id": path.name, "error": str(exc)})
    out_json = EVIDENCE / "v3_page_audit.json"
    out_json.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# v3 逐页结构排查", "", f"- 讲义数：{len(items)}", ""]
    for a in items:
        if "error" in a:
            lines += [f"## {a['id']}", "", f"- ❌ {a['error']}", ""]
            continue
        lines += [
            f"## {a['id']} · {a['title']}",
            "",
            f"- 资料页：{a['page_count']}；范围：{a['scope'][:1]}–{a['scope'][-1] if a['scope'] else '—'}（{len(a['scope'])} 页）",
            f"- 有 sections.json：{'是' if a['has_sections'] else '否'}" + (
                f"；block 引用页：{a['block_pages']}；缺 block 页：{a['missing_block_pages'] or '无'}"
                if a['has_sections'] else "；无法做 block 级页覆盖"),
            f"- 小节级引用缺页：{a['missing_section_pages'] or '无'}",
            f"- 语义审计：{'有' if a['audit_present'] else '无'}；状态 {a['audit_counts'] or '—'}",
            f"- 未审计页：{a['missing_audit_pages'] or '无'}",
            f"- partial：{a['partial_pages'] or '无'}；missing：{a['missing_pages'] or '无'}；visual：{a['visual_pages'] or '无'}",
            f"- PDF：{a['pdf']}",
            f"- 图：{a['figures']}；异常 {len(a['figures_bad'])}；缺资产 {a['missing_assets'] or '无'}",
            "",
        ]
    (EVIDENCE / "v3_page_audit.md").write_text("\n".join(lines), encoding="utf-8")
    for a in items:
        if "error" in a:
            print(a["id"], "ERROR", a["error"])
        else:
            mb = "n/a" if a["missing_block_pages"] is None else len(a["missing_block_pages"])
            print(f"{a['id']:24} pages={a['page_count']:3} scope={len(a['scope']):3} "
                  f"block={a['block_pages']:3} audit={a['audit_counts']} "
                  f"visual={len(a['visual_pages'])} missing_block={mb} figures={a['figures']}")
    print(out_json)


if __name__ == "__main__":
    main()
