"""Deterministic page/evidence coverage report for a lecture."""
from __future__ import annotations

from pathlib import Path

from tfv2.domain.lecture import BlockKind, LectureSpec


def build_coverage_matrix(spec: LectureSpec) -> dict:
    pages = {p: {"page": p, "sections": [], "blocks": 0, "figures": 0} for p in range(1, spec.page_count + 1)}
    blocks_without_source = 0
    sections_without_source = 0
    for sec in spec.sections:
        if not sec.source_refs:
            sections_without_source += 1
        for block in sec.blocks:
            refs = list(block.source_refs)
            if block.figure is not None:
                refs.append(block.figure.source)
            if block.kind != BlockKind.FIGURE and (block.text or "").strip() and not block.source_refs:
                blocks_without_source += 1
            for ref in refs:
                end = ref.page_end or ref.page_start
                for p in range(max(1, ref.page_start), min(spec.page_count, end) + 1):
                    entry = pages[p]
                    if sec.title not in entry["sections"]:
                        entry["sections"].append(sec.title)
                    if block.kind == BlockKind.FIGURE:
                        entry["figures"] += 1
                    else:
                        entry["blocks"] += 1
    covered = sum(1 for x in pages.values() if x["sections"])
    uncovered = [p for p, x in pages.items() if not x["sections"]]
    return {
        "page_count": spec.page_count,
        "covered_pages": covered,
        "uncovered_pages": uncovered,
        "coverage_percent": round(100 * covered / max(1, spec.page_count), 1),
        "blocks_without_source": blocks_without_source,
        "sections_without_source": sections_without_source,
        "pages": list(pages.values()),
    }


def coverage_matrix_markdown(matrix: dict) -> str:
    lines = ["# 覆盖矩阵", "",
             f"- 覆盖页：{matrix.get('covered_pages')}/{matrix.get('page_count')}",
             f"- 覆盖比例：{matrix.get('coverage_percent')}%",
             f"- 无来源块：{matrix.get('blocks_without_source')}",
             f"- 无来源小节：{matrix.get('sections_without_source')}", ""]
    if matrix.get("uncovered_pages"):
        lines += [f"- 未覆盖页：{matrix['uncovered_pages']}", ""]
    lines += ["| 页 | 小节 | 正文块 | 图 |", "|---|---|---:|---:|"]
    for p in matrix.get("pages") or []:
        if not p.get("sections"):
            continue
        lines.append(f"| {p['page']} | {'；'.join(p['sections'][:3])} | {p['blocks']} | {p['figures']} |")
    return "\n".join(lines) + "\n"


def save_coverage_matrix(matrix: dict, out_dir: str | Path) -> None:
    import json
    out = Path(out_dir)
    (out / "coverage_matrix.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "coverage_matrix.md").write_text(coverage_matrix_markdown(matrix), encoding="utf-8")
