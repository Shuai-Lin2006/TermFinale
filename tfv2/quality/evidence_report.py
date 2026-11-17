"""Block/claim evidence report, identical contract for every subject."""
from __future__ import annotations

from pathlib import Path

from tfv2.domain.lecture import BlockKind, LectureSpec
from tfv2.quality.trust import overlap


def build_evidence_report(spec: LectureSpec) -> list[dict]:
    rows: list[dict] = []
    for sec in spec.sections:
        for block in sec.blocks:
            text = (block.text or "").strip()
            if block.kind == BlockKind.FIGURE:
                continue
            refs = list(block.source_refs or [])
            quotes = [r.quote for r in refs if r.quote]
            if not refs:
                status = "missing"
            elif quotes and any(overlap(text, q) >= 0.1 for q in quotes):
                status = "quoted"
            elif quotes:
                status = "weak_quote"
            else:
                status = "page_only"
            rows.append({
                "section": sec.title, "block_id": block.id, "kind": str(block.kind.value),
                "text_chars": len(text), "pages": sorted({p for r in refs for p in range(r.page_start, (r.page_end or r.page_start) + 1)}),
                "refs": len(refs), "quotes": quotes[:3], "status": status,
            })
    return rows


def evidence_summary(rows: list[dict]) -> dict:
    total = len(rows)
    missing = sum(1 for x in rows if x["status"] == "missing")
    page_only = sum(1 for x in rows if x["status"] == "page_only")
    quoted = sum(1 for x in rows if x["status"] == "quoted")
    ratio = round(quoted / total, 3) if total else 0.0
    return {
        "total": total,
        "missing": missing,
        "page_only": page_only,
        "quoted": quoted,
        "quoted_ratio": ratio,
        # Presence is not evidence. A report only passes when most blocks have
        # a real, page-local quote and none are missing a source page.
        "passed": bool(total) and missing == 0 and ratio >= 0.6,
    }


def evidence_markdown(rows: list[dict]) -> str:
    summary = evidence_summary(rows)
    lines = ["# 证据报告", "",
             f"- 正文块：{summary['total']}",
             f"- 有 quote：{summary['quoted']}",
             f"- 仅页级：{summary['page_only']}",
             f"- 缺失来源：{summary['missing']}",
             f"- 有引用比例：{summary['quoted_ratio']:.0%}",
             f"- 结果：{'通过' if summary['passed'] else ('部分：引用覆盖率不足 60%' if summary['missing'] == 0 else '不通过：存在缺来源块')}", ""]
    lines += ["| 小节 | 类型 | 页 | 状态 | 片段 |", "|---|---|---|---|---|"]
    for x in rows:
        q = (x["quotes"][0] if x["quotes"] else "").replace("|", "\\|")[:60]
        lines.append(f"| {x['section'][:20]} | {x['kind']} | {x['pages'][:4]} | {x['status']} | {q} |")
    return "\n".join(lines) + "\n"


def save_evidence_report(rows: list[dict], out: str | Path) -> dict:
    import json
    p = Path(out)
    summary = evidence_summary(rows)
    (p / "evidence_report.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    (p / "evidence_report.md").write_text(evidence_markdown(rows), encoding="utf-8")
    return summary
