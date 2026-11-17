"""truth 评测：用人工填写的 must_contain / must_not_contain 对页面正文打分。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "docs" / "golden" / "truth_cases.json"


def page_text(artifact_id: str, page: int) -> str:
    p = ROOT / "docs" / "evidence" / artifact_id / "sections.json"
    if not p.is_file():
        return ""
    data = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for sec in data if isinstance(data, list) else []:
        for b in sec.get("blocks") or []:
            refs = b.get("source_refs") or []
            if any(int(r.get("page_start", 0)) <= page <= int(r.get("page_end") or r.get("page_start", 0)) for r in refs):
                out.append(str(b.get("text") or ""))
    return "\n".join(out)


def main() -> None:
    data = json.loads(CASES.read_text(encoding="utf-8")) if CASES.is_file() else {"cases": []}
    cases = data.get("cases") or []
    passed = 0
    for i, c in enumerate(cases, 1):
        text = page_text(str(c.get("artifact_id") or ""), int(c.get("page") or 0))
        missing = [x for x in c.get("must_contain") or [] if x not in text]
        bad = [x for x in c.get("must_not_contain") or [] if x in text]
        ok = bool(text) and not missing and not bad
        passed += 1 if ok else 0
        print(f"{i}. {'PASS' if ok else 'FAIL'} page={c.get('page')} missing={missing} bad={bad}")
    print(f"truth cases={len(cases)} passed={passed}")
    if cases and passed != len(cases):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
