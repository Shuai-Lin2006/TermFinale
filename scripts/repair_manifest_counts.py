"""修正 manifest 里虚报的页数：记录实际构建页数，保留用户请求页数。

只改 page_count 与 source_pages.json 不一致的产物；不改 sections/PDF。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "data" / "artifacts"


def main() -> None:
    fixed = []
    for d in sorted(ARTIFACTS.iterdir()):
        man_p, src_p = d / "manifest.json", d / "source_pages.json"
        if not man_p.is_file() or not src_p.is_file():
            continue
        try:
            man = json.loads(man_p.read_text(encoding="utf-8"))
            src = json.loads(src_p.read_text(encoding="utf-8"))
        except Exception:
            continue
        claimed = man.get("page_count")
        actual = int(src.get("page_count") or len(src.get("pages") or []))
        if not isinstance(claimed, int) or claimed == actual:
            continue
        man["requested_page_count"] = claimed
        man["page_count"] = actual
        man["scope_pages"] = list(range(1, actual + 1))
        man["page_count_corrected_at"] = "2026-11-16"
        man["page_count_correction"] = (
            f"原 manifest 记录请求页数 {claimed}，实际构建 {actual} 页；已按实际页数修正，"
            "请求页数保留在 requested_page_count。"
        )
        man_p.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
        fixed.append((d.name, claimed, actual))
    for name, claimed, actual in fixed:
        print(f"fixed {name}: {claimed} -> {actual}")
    if not fixed:
        print("没有需要修正的 manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
