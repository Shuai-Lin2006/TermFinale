"""机器验收：在库生成物的结构、分值、重复题、图片数据、页覆盖。"""
from __future__ import annotations

import base64
import io
import json
import sqlite3
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence" / "golden_eval.json"


def check_exam(doc: dict) -> list[str]:
    issues = []
    content = doc.get("content") if isinstance(doc.get("content"), dict) and "sections" not in doc else doc
    sections = content.get("sections") or []
    qs = [q for s in sections for q in s.get("questions") or []]
    total = sum(float(q.get("score") or 0) for q in qs)
    if round(total, 1) != 100:
        issues.append(f"总分 {total:.1f} != 100")
    if len(qs) < 12:
        issues.append(f"题量 {len(qs)} < 12")
    stems = [str(q.get("stem") or "").strip() for q in qs]
    dup = [x for x, n in Counter(stems).items() if n > 1]
    if dup:
        issues.append(f"重复题干 {len(dup)}")
    for i, q in enumerate(qs, 1):
        if not q.get("source_page"):
            issues.append(f"Q{i} 缺页码")
        if q.get("qtype") == "choice":
            if len(q.get("options") or []) != 4:
                issues.append(f"Q{i} 选项不是 4 个")
            if q.get("answer") not in range(4):
                issues.append(f"Q{i} 答案非法")
        data = q.get("figure_data") or ""
        if data:
            try:
                raw = base64.b64decode(data.split(",", 1)[1])
                im = Image.open(io.BytesIO(raw)); im.verify()
            except Exception:
                issues.append(f"Q{i} figure_data 损坏")
    return issues


def main() -> None:
    conn = sqlite3.connect(ROOT / "data" / "product.sqlite3")
    rows = conn.execute("SELECT id,kind,title,status,content FROM documents ORDER BY created_at DESC").fetchall()
    results = []
    for did, kind, title, status, content in rows:
        try:
            doc = json.loads(content)
        except Exception:
            continue
        issues = check_exam(doc) if kind == "exam" and status == "validated" else []
        if kind in ("extract_points", "mindmap", "extract_questions"):
            cov = doc.get("coverage") or {}
            if cov and cov.get("coverage") is not None and cov["coverage"] < 0.98 and status == "validated":
                issues.append("validated 但覆盖率 <98%")
        results.append({"id": did, "kind": kind, "title": title, "status": status, "issues": issues})
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = [r for r in results if r["issues"]]
    for r in bad:
        print(r["id"][:8], r["kind"], r["status"], r["issues"][:5])
    print(f"documents={len(results)} bad={len(bad)} -> {OUT}")


if __name__ == "__main__":
    main()
